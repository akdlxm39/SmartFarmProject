#!/usr/bin/env python3
"""PC socket server: command the Raspberry Pi to capture one JPG frame and receive it.

Protocol:
- Pi connects to this server and waits for line-delimited JSON commands.
- Server sends: {"type":"capture","request_id":"...","width":1280,"height":720,"quality":90}\n
- Pi responds with a binary frame packet:
    4 bytes magic: b"SFJ1"
    4 bytes metadata JSON length, unsigned big-endian
    8 bytes payload length, unsigned big-endian
    N bytes UTF-8 JSON metadata
    M bytes JPEG payload

This keeps socket communication, but changes direction/control:
PC server -> "capture now" command -> Pi captures one JPG -> Pi sends encoded JPG bytes back.
"""

from __future__ import annotations

import argparse
import json
import queue
import socket
import struct
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

MAGIC = b"SFJ1"
HEADER_STRUCT = struct.Struct("!4sIQ")
CHUNK_SIZE = 1024 * 1024


def recv_exact(sock: socket.socket, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(min(CHUNK_SIZE, size - len(data)))
        if not chunk:
            raise ConnectionError(f"socket closed while receiving {size} bytes")
        data.extend(chunk)
    return bytes(data)


def read_jpeg_packet(sock: socket.socket) -> tuple[dict[str, Any], bytes]:
    header = recv_exact(sock, HEADER_STRUCT.size)
    magic, metadata_len, payload_len = HEADER_STRUCT.unpack(header)
    if magic != MAGIC:
        raise ValueError(f"bad magic {magic!r}; expected {MAGIC!r}")
    if metadata_len > 1024 * 1024:
        raise ValueError(f"metadata too large: {metadata_len}")
    metadata = json.loads(recv_exact(sock, metadata_len).decode("utf-8"))
    payload = recv_exact(sock, payload_len)
    return metadata, payload


def write_latest_marker(save_dir: Path, saved_path: Path, metadata: dict[str, Any]) -> None:
    marker = {
        "latest_file": saved_path.name,
        "latest_path": str(saved_path),
        "received_at": datetime.now().isoformat(timespec="seconds"),
        "metadata": metadata,
    }
    (save_dir / "latest_jpeg.json").write_text(json.dumps(marker, ensure_ascii=False, indent=2), encoding="utf-8")


def save_jpeg(save_dir: Path, metadata: dict[str, Any], payload: bytes) -> Path:
    request_id = str(metadata.get("request_id") or datetime.now().strftime("%Y%m%d_%H%M%S"))
    safe_request_id = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in request_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = save_dir / f"{timestamp}_{safe_request_id}.jpg"
    path.write_bytes(payload)
    write_latest_marker(save_dir, path, metadata)
    return path


def display_jpeg(payload: bytes, window_name: str = "SmartFarm JPG Capture") -> bool:
    import cv2  # type: ignore[import-not-found]
    import numpy as np  # type: ignore[import-not-found]

    arr = np.frombuffer(payload, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        print("[display:error] cv2.imdecode failed", flush=True)
        return False
    cv2.imshow(window_name, frame)
    cv2.waitKey(1)
    return True


def make_capture_command(args: argparse.Namespace, request_id: str) -> dict[str, Any]:
    return {
        "type": "capture",
        "request_id": request_id,
        "width": args.width,
        "height": args.height,
        "quality": args.quality,
        "timeout_ms": args.camera_timeout_ms,
    }


def command_loop(conn: socket.socket, peer: tuple[str, int], args: argparse.Namespace, save_dir: Path) -> None:
    print(f"[server] client connected: {peer[0]}:{peer[1]}", flush=True)
    captures_done = 0

    def send_capture() -> bool:
        nonlocal captures_done
        request_id = datetime.now().strftime("req_%Y%m%d_%H%M%S_%f")
        command = make_capture_command(args, request_id)
        conn.sendall((json.dumps(command, ensure_ascii=False) + "\n").encode("utf-8"))
        print(f"[server] sent capture command: {request_id}", flush=True)
        metadata, payload = read_jpeg_packet(conn)
        if metadata.get("status") != "ok":
            print(f"[server:error] client returned {metadata}", flush=True)
            return False
        saved_path = save_jpeg(save_dir, metadata, payload)
        print(f"[server] received JPG -> {saved_path} ({len(payload)} bytes)", flush=True)
        if args.show_window:
            display_jpeg(payload)
        captures_done += 1
        return True

    if args.auto_capture:
        while args.count <= 0 or captures_done < args.count:
            send_capture()
            if args.count > 0 and captures_done >= args.count:
                break
            time.sleep(args.interval)
        return

    print("[server] press Enter to capture one JPG, or type q then Enter to quit", flush=True)
    while True:
        line = input("capture> ").strip().lower()
        if line in {"q", "quit", "exit"}:
            break
        send_capture()


def run(args: argparse.Namespace) -> None:
    save_dir = Path(args.save_dir).expanduser().resolve()
    save_dir.mkdir(parents=True, exist_ok=True)

    if args.show_window:
        # Import early to fail before accepting a client if GUI dependencies are missing.
        import cv2  # type: ignore[import-not-found]  # noqa: F401

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((args.host, args.port))
        server.listen(1)
        print(f"[server] listening on {args.host}:{args.port}, save_dir={save_dir}", flush=True)
        conn, peer = server.accept()
        with conn:
            command_loop(conn, peer, args, save_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ask a Raspberry Pi client to capture one JPG frame and send it back over a socket.")
    parser.add_argument("--host", default="0.0.0.0", help="server listen host")
    parser.add_argument("--port", type=int, default=5002, help="command/response socket port")
    parser.add_argument("--save-dir", default="incoming_jpegs", help="directory to save received JPGs")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--quality", type=int, default=90)
    parser.add_argument("--camera-timeout-ms", type=int, default=800, help="Pi camera warmup/capture timeout")
    parser.add_argument("--show-window", action="store_true", help="display received JPG with OpenCV imshow")
    parser.add_argument("--auto-capture", action="store_true", help="capture automatically without interactive input")
    parser.add_argument("--count", type=int, default=1, help="number of captures in auto mode; <=0 means forever")
    parser.add_argument("--interval", type=float, default=1.0, help="seconds between auto captures")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())

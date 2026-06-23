#!/usr/bin/env python3
"""Raspberry Pi socket client: wait for capture commands, capture one JPG, send bytes back.

Target: Raspberry Pi 5 + Raspberry Pi Camera Module 3 Wide.
The PC is the socket server. This client connects to it, waits for a JSON command, captures one JPG frame with rpicam-still/rpicam-jpeg, and sends encoded JPG bytes back.

For PC-side protocol tests without a camera, use --mock-source path/to/image.jpg.
"""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

MAGIC = b"SFJ1"
HEADER_STRUCT = struct.Struct("!4sIQ")
CHUNK_SIZE = 1024 * 1024


def find_command(candidates: list[str]) -> str | None:
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found
    return None


def read_json_line(sock_file) -> dict[str, Any] | None:
    line = sock_file.readline()
    if not line:
        return None
    return json.loads(line.decode("utf-8"))


def send_packet(sock: socket.socket, metadata: dict[str, Any], payload: bytes) -> None:
    metadata_bytes = json.dumps(metadata, ensure_ascii=False).encode("utf-8")
    header = HEADER_STRUCT.pack(MAGIC, len(metadata_bytes), len(payload))
    sock.sendall(header)
    sock.sendall(metadata_bytes)
    sock.sendall(payload)


def capture_jpg(output_path: Path, width: int, height: int, quality: int, timeout_ms: int) -> Path:
    # rpicam-still and rpicam-jpeg are both available on recent Raspberry Pi OS.
    command = find_command(["rpicam-still", "libcamera-still", "rpicam-jpeg", "libcamera-jpeg"])
    if not command:
        raise RuntimeError("rpicam-still/libcamera-still/rpicam-jpeg/libcamera-jpeg not found")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    base_cmd = [
        command,
        "-t", str(timeout_ms),
        "--width", str(width),
        "--height", str(height),
        "--quality", str(quality),
        "--nopreview",
        "-o", str(output_path),
    ]
    print("[cmd]", " ".join(base_cmd), flush=True)
    result = subprocess.run(base_cmd, capture_output=True, text=True, timeout=max(10, timeout_ms // 1000 + 10), check=False)
    if result.stdout.strip():
        print(result.stdout.strip(), flush=True)
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr, flush=True)
    if result.returncode != 0:
        raise RuntimeError(f"camera capture failed with code {result.returncode}")
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(f"capture produced no data: {output_path}")
    return output_path


def handle_capture(command: dict[str, Any], args: argparse.Namespace) -> tuple[dict[str, Any], bytes]:
    request_id = str(command.get("request_id") or datetime.now().strftime("req_%Y%m%d_%H%M%S"))
    width = int(command.get("width") or args.width)
    height = int(command.get("height") or args.height)
    quality = int(command.get("quality") or args.quality)
    timeout_ms = int(command.get("timeout_ms") or args.camera_timeout_ms)
    captured_at = datetime.now().isoformat(timespec="seconds")

    if args.mock_source:
        jpg_path = Path(args.mock_source).expanduser().resolve()
        if not jpg_path.exists():
            raise FileNotFoundError(jpg_path)
        payload = jpg_path.read_bytes()
        source = "mock-source"
    else:
        output_dir = Path(args.output_dir).expanduser().resolve()
        filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
        jpg_path = capture_jpg(output_dir / filename, width, height, quality, timeout_ms)
        payload = jpg_path.read_bytes()
        source = "rpicam"

    metadata = {
        "status": "ok",
        "type": "capture_result",
        "request_id": request_id,
        "captured_at": captured_at,
        "sender": args.sender,
        "camera_model": args.camera_model,
        "source": source,
        "filename": jpg_path.name,
        "format": "jpg",
        "width": width,
        "height": height,
        "quality": quality,
        "payload_bytes": len(payload),
    }
    return metadata, payload


def handle_command(sock: socket.socket, command: dict[str, Any], args: argparse.Namespace) -> None:
    if command.get("type") != "capture":
        metadata = {
            "status": "error",
            "type": "error",
            "message": f"unsupported command type: {command.get('type')}",
            "request_id": command.get("request_id"),
            "payload_bytes": 0,
        }
        send_packet(sock, metadata, b"")
        return

    try:
        metadata, payload = handle_capture(command, args)
    except Exception as exc:
        metadata = {
            "status": "error",
            "type": "error",
            "request_id": command.get("request_id"),
            "message": f"{type(exc).__name__}: {exc}",
            "payload_bytes": 0,
        }
        payload = b""
    send_packet(sock, metadata, payload)
    print(f"[send] {metadata.get('status')} request={metadata.get('request_id')} bytes={len(payload)}", flush=True)


def configure_command_idle_timeout(sock: socket.socket, args: argparse.Namespace) -> None:
    """Configure timeout while waiting for capture commands after connect.

    socket.create_connection(timeout=...) leaves that timeout on the socket. If
    we keep it, the Pi client disconnects while Dobot is still moving to the
    camera pose. A value <= 0 means wait forever, which is the default for the
    persistent Dobot↔vision daemon workflow.
    """
    idle_timeout = float(getattr(args, "command_idle_timeout_sec", 0.0) or 0.0)
    sock.settimeout(None if idle_timeout <= 0 else idle_timeout)


def client_loop(args: argparse.Namespace) -> None:
    while True:
        try:
            print(f"[client] connecting to {args.server_host}:{args.server_port}", flush=True)
            with socket.create_connection((args.server_host, args.server_port), timeout=args.connect_timeout_sec) as sock:
                configure_command_idle_timeout(sock, args)
                print("[client] connected; waiting for capture commands", flush=True)
                sock_file = sock.makefile("rb")
                while True:
                    command = read_json_line(sock_file)
                    if command is None:
                        print("[client] server closed connection", flush=True)
                        break
                    print(f"[client] command: {command}", flush=True)
                    handle_command(sock, command, args)
            if not args.reconnect:
                return
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            print(f"[client:error] {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            if not args.reconnect:
                raise
            time.sleep(args.reconnect_delay)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wait for socket capture commands and send one encoded JPG frame back.")
    parser.add_argument("--server-host", required=True, help="PC socket server IP/hostname")
    parser.add_argument("--server-port", type=int, default=5002)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--quality", type=int, default=90)
    parser.add_argument("--camera-timeout-ms", type=int, default=800)
    parser.add_argument("--output-dir", default="captures_jpg")
    parser.add_argument("--sender", default="raspberry-pi5")
    parser.add_argument("--camera-model", default="Raspberry Pi Camera Module 3 Wide")
    parser.add_argument("--mock-source", default="", help="send this existing JPG instead of capturing camera")
    parser.add_argument("--connect-timeout-sec", type=float, default=10.0, help="TCP connect timeout")
    parser.add_argument(
        "--command-idle-timeout-sec",
        type=float,
        default=0.0,
        help="Timeout while waiting for capture commands after connect; <=0 waits forever",
    )
    parser.add_argument("--reconnect", action="store_true", help="reconnect forever if server disconnects")
    parser.add_argument("--reconnect-delay", type=float, default=2.0)
    return parser.parse_args()


if __name__ == "__main__":
    client_loop(parse_args())

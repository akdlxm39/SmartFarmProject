#!/usr/bin/env python3
"""Bridge Dobot capture requests to a Raspberry Pi JPG capture client.

Two sockets are used:
- Pi socket: Raspberry Pi connects here and waits for capture commands.
- Control socket: local Dobot/ROS process connects here and requests a capture.

For now, any successfully received JPG returns a temporary quality_status="normal".
Later this daemon is the extension point for OpenCV/YOLO inference.
"""

from __future__ import annotations

import argparse
import json
import socket
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from vision_socket_protocol import read_jpeg_packet, read_json_line, send_json_line

TEMPORARY_SUCCESS_QUALITY_STATUS = "normal"


def sanitize_path_component(value: object, fallback: str) -> str:
    raw = str(value or fallback)
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in raw)
    return safe or fallback


def angle_file_stem(angle_deg: object) -> str:
    angle = float(angle_deg)
    if angle.is_integer():
        integer_angle = int(angle)
        if integer_angle == 0:
            label = "000"
        else:
            label = str(integer_angle)
    else:
        label = f"{angle:.1f}".rstrip("0").rstrip(".")
    return f"angle_{label}"


def append_session_metadata(session_path: Path, response: dict[str, Any]) -> None:
    if session_path.exists():
        try:
            session = json.loads(session_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            session = {"captures": []}
    else:
        session = {
            "sequence_id": response.get("sequence_id"),
            "harvest_index": response.get("harvest_index"),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "temporary_quality_rule": "all successful captures are treated as normal until OpenCV/YOLO inference is added",
            "captures": [],
        }
    session.setdefault("captures", []).append(response)
    session["updated_at"] = datetime.now().isoformat(timespec="seconds")
    session_path.write_text(json.dumps(session, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def save_capture_result(
    save_dir: Path | str,
    request: dict[str, Any],
    pi_metadata: dict[str, Any],
    payload: bytes,
) -> dict[str, Any]:
    """Save one JPG response and return the local-control response JSON."""
    root = Path(save_dir).expanduser().resolve()
    sequence_id = sanitize_path_component(
        request.get("sequence_id"),
        datetime.now().strftime("sequence_%Y%m%d_%H%M%S"),
    )
    angle_stem = angle_file_stem(request.get("angle_deg", 0))
    session_dir = root / sequence_id
    session_dir.mkdir(parents=True, exist_ok=True)
    saved_path = session_dir / f"{angle_stem}.jpg"
    saved_path.write_bytes(payload)

    response = {
        "status": "ok",
        "type": "capture_result",
        "sequence_id": sequence_id,
        "harvest_index": request.get("harvest_index"),
        "angle_deg": request.get("angle_deg"),
        "request_id": pi_metadata.get("request_id") or request.get("request_id"),
        "saved_path": str(saved_path),
        "payload_bytes": len(payload),
        "quality_status": TEMPORARY_SUCCESS_QUALITY_STATUS,
        "quality_source": "temporary_all_requested_captures_success",
        "metadata": pi_metadata,
        "received_at": datetime.now().isoformat(timespec="seconds"),
    }
    append_session_metadata(session_dir / "capture_session.json", response)
    (root / "latest_jpeg.json").write_text(json.dumps(response, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return response


def build_pi_capture_command(request: dict[str, Any]) -> dict[str, Any]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    sequence_id = sanitize_path_component(request.get("sequence_id"), "sequence")
    angle = angle_file_stem(request.get("angle_deg", 0))
    return {
        "type": "capture",
        "request_id": f"{sequence_id}_{angle}_{timestamp}",
        "width": int(request.get("width") or 1280),
        "height": int(request.get("height") or 720),
        "quality": int(request.get("quality") or 90),
        "timeout_ms": int(request.get("timeout_ms") or 800),
    }


def accept_pi_client(pi_server: socket.socket) -> tuple[socket.socket, tuple[str, int]]:
    """Wait for one Raspberry Pi client and return its connected socket."""
    print("[daemon] waiting for Raspberry Pi client connection", flush=True)
    pi_conn, pi_peer = pi_server.accept()
    pi_conn.settimeout(None)
    print(f"[daemon] Raspberry Pi connected: {pi_peer[0]}:{pi_peer[1]}", flush=True)
    return pi_conn, pi_peer


def capture_once_with_pi(pi_conn: socket.socket, request: dict[str, Any], save_dir: Path) -> dict[str, Any]:
    pi_command = build_pi_capture_command(request)
    send_json_line(pi_conn, pi_command)
    pi_metadata, payload = read_jpeg_packet(pi_conn)
    if pi_metadata.get("status") != "ok":
        return {
            "status": "error",
            "type": "capture_result",
            "message": "Raspberry Pi capture failed",
            "metadata": pi_metadata,
            "quality_status": "unknown",
        }
    return save_capture_result(save_dir, request, pi_metadata, payload)


def handle_control_request(
    control_conn: socket.socket,
    pi_conn: socket.socket,
    save_dir: Path,
    pi_server: socket.socket,
) -> socket.socket:
    control_file = control_conn.makefile("rb")
    request = read_json_line(control_file)
    if request is None:
        return pi_conn
    if request.get("type") != "capture":
        send_json_line(
            control_conn,
            {
                "status": "error",
                "type": "error",
                "message": f"unsupported request type: {request.get('type')}",
            },
        )
        return pi_conn

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = capture_once_with_pi(pi_conn, request, save_dir)
            send_json_line(control_conn, response)
            return pi_conn
        except Exception as exc:
            last_error = exc
            print(
                f"[daemon:error] Raspberry Pi socket failed during capture "
                f"(attempt {attempt + 1}/2): {type(exc).__name__}: {exc}",
                flush=True,
            )
            try:
                pi_conn.close()
            except OSError:
                pass
            if attempt == 0:
                print("[daemon] waiting for Raspberry Pi reconnect before retrying request", flush=True)
                pi_conn, _ = accept_pi_client(pi_server)
                continue
            send_json_line(
                control_conn,
                {
                    "status": "error",
                    "type": "capture_result",
                    "message": f"{type(exc).__name__}: {exc}",
                    "quality_status": "unknown",
                },
            )
            return pi_conn
    raise RuntimeError(f"unreachable capture retry state: {last_error}")


def run(args: argparse.Namespace) -> None:
    save_dir = Path(args.save_dir).expanduser().resolve()
    save_dir.mkdir(parents=True, exist_ok=True)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as pi_server:
        pi_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        pi_server.bind((args.pi_host, args.pi_port))
        pi_server.listen(1)
        print(f"[daemon] waiting for Raspberry Pi on {args.pi_host}:{args.pi_port}", flush=True)
        pi_conn, _ = accept_pi_client(pi_server)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as control_server:
                control_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                control_server.bind((args.control_host, args.control_port))
                control_server.listen(8)
                print(
                    f"[daemon] control listening on {args.control_host}:{args.control_port}, save_dir={save_dir}",
                    flush=True,
                )
                captures_done = 0
                while args.count <= 0 or captures_done < args.count:
                    control_conn, control_peer = control_server.accept()
                    with control_conn:
                        print(f"[daemon] control request from {control_peer[0]}:{control_peer[1]}", flush=True)
                        pi_conn = handle_control_request(control_conn, pi_conn, save_dir, pi_server)
                        captures_done += 1
                    if args.interval > 0:
                        time.sleep(args.interval)
        finally:
            pi_conn.close()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bridge local Dobot capture requests to a Raspberry Pi JPG client.")
    parser.add_argument("--pi-host", default="0.0.0.0", help="host/IP for Raspberry Pi client socket")
    parser.add_argument("--pi-port", type=int, default=5002, help="port for Raspberry Pi client socket")
    parser.add_argument("--control-host", default="127.0.0.1", help="host/IP for local Dobot control socket")
    parser.add_argument("--control-port", type=int, default=5012, help="port for local Dobot control socket")
    parser.add_argument("--save-dir", default="incoming_jpegs", help="directory to save received JPGs")
    parser.add_argument("--count", type=int, default=0, help="number of control captures to serve; <=0 means forever")
    parser.add_argument("--interval", type=float, default=0.0, help="optional delay between control requests")
    return parser.parse_args(argv)


if __name__ == "__main__":
    run(parse_args())

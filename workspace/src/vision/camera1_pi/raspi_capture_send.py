#!/usr/bin/env python3
"""Raspberry Pi side: check camera, capture a short video, then send it to the PC over TCP.

Target hardware: Raspberry Pi 5 + Raspberry Pi Camera Module 3 Wide on Raspberry Pi OS.
The script prefers rpicam-vid/libcamera-vid because they are standard on recent Raspberry Pi OS images.
For local tests without a camera, use --mock-source path/to/video.
"""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import struct
import subprocess
import sys
from datetime import datetime
from pathlib import Path

MAGIC = b"SFV1"
HEADER_STRUCT = struct.Struct("!4sIQ")
CHUNK_SIZE = 1024 * 1024


def find_command(candidates: list[str]) -> str | None:
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found
    return None


def run_command(command: list[str], timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    print("[cmd]", " ".join(command), flush=True)
    return subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)


def check_camera() -> str:
    hello_cmd = find_command(["rpicam-hello", "libcamera-hello"])
    if not hello_cmd:
        raise RuntimeError("rpicam-hello/libcamera-hello not found. Install Raspberry Pi camera apps first.")
    result = run_command([hello_cmd, "--list-cameras"], timeout=20)
    output = (result.stdout + result.stderr).strip()
    print(output, flush=True)
    if result.returncode != 0:
        raise RuntimeError(f"camera list failed with code {result.returncode}")
    if "Available cameras" not in output and "0 :" not in output and "imx708" not in output.lower():
        print("[warn] camera command succeeded, but output did not clearly list a camera", flush=True)
    return output


def capture_video(output_path: Path, duration_sec: float, width: int, height: int, fps: int) -> Path:
    vid_cmd = find_command(["rpicam-vid", "libcamera-vid"])
    if not vid_cmd:
        raise RuntimeError("rpicam-vid/libcamera-vid not found. Install Raspberry Pi camera apps first.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = max(1000, int(duration_sec * 1000))
    command = [
        vid_cmd,
        "-t", str(duration_ms),
        "--width", str(width),
        "--height", str(height),
        "--framerate", str(fps),
        "--codec", "h264",
        "--inline",
        "--nopreview",
        "-o", str(output_path),
    ]
    result = run_command(command, timeout=int(duration_sec) + 30)
    if result.stdout.strip():
        print(result.stdout.strip(), flush=True)
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr, flush=True)
    if result.returncode != 0:
        raise RuntimeError(f"video capture failed with code {result.returncode}")
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(f"capture produced no data: {output_path}")
    print(f"[capture] saved {output_path} ({output_path.stat().st_size} bytes)", flush=True)
    return output_path


def send_file(host: str, port: int, file_path: Path, metadata: dict) -> str:
    payload_len = file_path.stat().st_size
    metadata = dict(metadata)
    metadata.setdefault("filename", file_path.name)
    metadata.setdefault("payload_bytes", payload_len)
    metadata_bytes = json.dumps(metadata, ensure_ascii=False).encode("utf-8")
    header = HEADER_STRUCT.pack(MAGIC, len(metadata_bytes), payload_len)

    print(f"[send] connecting to {host}:{port}", flush=True)
    with socket.create_connection((host, port), timeout=15) as sock:
        sock.sendall(header)
        sock.sendall(metadata_bytes)
        with file_path.open("rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                sock.sendall(chunk)
        sock.shutdown(socket.SHUT_WR)
        ack = sock.recv(4096).decode("utf-8", errors="replace").strip()
    print(f"[send] server response: {ack}", flush=True)
    if not ack.startswith("OK"):
        raise RuntimeError(f"server returned error: {ack}")
    return ack


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture video on Raspberry Pi and send it to a PC over TCP socket.")
    parser.add_argument("--pc-host", required=True, help="PC receiver IP/hostname, e.g. 192.168.110.109")
    parser.add_argument("--pc-port", type=int, default=5001, help="PC receiver TCP port")
    parser.add_argument("--duration", type=float, default=5.0, help="capture duration seconds")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--output-dir", default="captures", help="local directory on Raspberry Pi for captured videos")
    parser.add_argument("--filename", default="", help="optional output filename; default uses timestamp")
    parser.add_argument("--camera-model", default="Raspberry Pi Camera Module 3 Wide")
    parser.add_argument("--mock-source", default="", help="send an existing file instead of checking/capturing camera")
    parser.add_argument("--skip-camera-check", action="store_true", help="capture without running camera list first")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = datetime.now().isoformat(timespec="seconds")

    if args.mock_source:
        video_path = Path(args.mock_source).expanduser().resolve()
        if not video_path.exists():
            raise FileNotFoundError(video_path)
        camera_report = "mock-source; camera not checked"
        print(f"[mock] sending existing file {video_path}", flush=True)
    else:
        camera_report = "camera check skipped"
        if not args.skip_camera_check:
            camera_report = check_camera()
        output_dir = Path(args.output_dir).expanduser().resolve()
        filename = args.filename or f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.h264"
        if not Path(filename).suffix:
            filename += ".h264"
        video_path = capture_video(output_dir / filename, args.duration, args.width, args.height, args.fps)

    metadata = {
        "filename": video_path.name,
        "captured_at": started_at,
        "sender": "raspberry-pi5",
        "camera_model": args.camera_model,
        "duration_sec": args.duration,
        "width": args.width,
        "height": args.height,
        "fps": args.fps,
        "camera_report": camera_report[:4000],
    }
    send_file(args.pc_host, args.pc_port, video_path, metadata)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[error] {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1)

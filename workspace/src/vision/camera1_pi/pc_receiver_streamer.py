#!/usr/bin/env python3
"""PC side: receive a video file over a raw TCP socket and optionally display it with OpenCV.

Protocol SFV1:
  client -> server:
    4 bytes  magic: b"SFV1"
    4 bytes  metadata JSON length, unsigned big-endian
    8 bytes  payload byte length, unsigned big-endian
    N bytes  UTF-8 JSON metadata
    M bytes  video payload
  server -> client:
    b"OK <saved_path>\n" on success

Modes:
- default: receive files and keep them on disk
- --show-window: after each receive, remux the file to MP4 if needed and play it with cv2.imshow
- --http-port / --no-http: keep or disable the lightweight HTTP endpoint
"""

from __future__ import annotations

import argparse
import html
import json
import mimetypes
import queue
import shutil
import socketserver
import struct
import subprocess
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

MAGIC = b"SFV1"
HEADER_STRUCT = struct.Struct("!4sIQ")  # magic, metadata_len, payload_len
CHUNK_SIZE = 1024 * 1024


def recv_exact(sock, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(min(CHUNK_SIZE, size - len(data)))
        if not chunk:
            raise ConnectionError(f"socket closed while receiving {size} bytes")
        data.extend(chunk)
    return bytes(data)


def safe_filename(name: str) -> str:
    cleaned = Path(name).name.replace("\x00", "")
    return cleaned or f"received_{datetime.now().strftime('%Y%m%d_%H%M%S')}.h264"


def write_latest_marker(save_dir: Path, saved_path: Path, metadata: dict[str, Any]) -> None:
    marker = {
        "latest_file": saved_path.name,
        "latest_path": str(saved_path),
        "received_at": datetime.now().isoformat(timespec="seconds"),
        "metadata": metadata,
    }
    (save_dir / "latest.json").write_text(json.dumps(marker, ensure_ascii=False, indent=2), encoding="utf-8")


def remux_for_display(source_path: Path, fps_hint: int | float | None = None) -> Path:
    if source_path.suffix.lower() == ".mp4":
        return source_path

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return source_path

    display_path = source_path.with_suffix(".mp4")
    command = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
    if fps_hint:
        command += ["-r", str(fps_hint)]
    command += ["-i", str(source_path), "-c", "copy", str(display_path)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"ffmpeg remux failed: {stderr}")
    return display_path


def start_display_worker(display_queue: queue.Queue[object]) -> threading.Thread:
    def worker() -> None:
        import cv2  # type: ignore[import-not-found]  # lazy import so non-display mode does not require OpenCV

        window_name = "SmartFarm Vision Receiver"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        print("[display] OpenCV window ready. Press q inside the window to close playback.", flush=True)
        while True:
            item = display_queue.get()
            if item is None:
                break
            file_path, metadata = item  # type: ignore[misc]
            fps_hint = metadata.get("fps")
            try:
                playable = remux_for_display(file_path, fps_hint=fps_hint)
            except Exception as exc:
                print(f"[display:error] remux failed for {file_path}: {exc}", flush=True)
                playable = file_path

            cap = cv2.VideoCapture(str(playable))
            if not cap.isOpened():
                print(f"[display:error] could not open {playable}", flush=True)
                continue

            fps = cap.get(cv2.CAP_PROP_FPS)
            if not fps or fps <= 1e-6:
                fps = float(fps_hint or 30.0)
            delay_ms = max(1, int(1000 / fps))
            print(f"[display] playing {playable} at ~{fps:.2f} FPS", flush=True)
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                overlay = f"{playable.name} | q: stop current clip"
                cv2.putText(frame, overlay, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
                cv2.imshow(window_name, frame)
                key = cv2.waitKey(delay_ms) & 0xFF
                if key == ord("q"):
                    break
            cap.release()
        cv2.destroyAllWindows()

    thread = threading.Thread(target=worker, name="opencv-display", daemon=True)
    thread.start()
    return thread


class VideoReceiveHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        save_dir: Path = self.server.save_dir  # type: ignore[attr-defined]
        display_queue = getattr(self.server, "display_queue", None)
        peer = f"{self.client_address[0]}:{self.client_address[1]}"
        try:
            header = recv_exact(self.request, HEADER_STRUCT.size)
            magic, metadata_len, payload_len = HEADER_STRUCT.unpack(header)
            if magic != MAGIC:
                raise ValueError(f"bad magic {magic!r}; expected {MAGIC!r}")
            if metadata_len > 1024 * 1024:
                raise ValueError(f"metadata too large: {metadata_len}")

            metadata = json.loads(recv_exact(self.request, metadata_len).decode("utf-8"))
            filename = safe_filename(str(metadata.get("filename", "capture.h264")))
            stem = Path(filename).stem
            suffix = Path(filename).suffix or ".h264"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_path = save_dir / f"{timestamp}_{stem}{suffix}"
            temp_path = saved_path.with_suffix(saved_path.suffix + ".part")

            remaining = payload_len
            with temp_path.open("wb") as f:
                while remaining:
                    chunk = self.request.recv(min(CHUNK_SIZE, remaining))
                    if not chunk:
                        raise ConnectionError(f"socket closed with {remaining} bytes remaining")
                    f.write(chunk)
                    remaining -= len(chunk)
            temp_path.replace(saved_path)
            write_latest_marker(save_dir, saved_path, metadata)
            if display_queue is not None:
                display_queue.put((saved_path, metadata))
            msg = f"OK {saved_path}\n"
            self.request.sendall(msg.encode("utf-8"))
            print(f"[receive] {peer} -> {saved_path} ({payload_len} bytes)", flush=True)
        except Exception as exc:  # keep server alive after malformed requests
            err = f"ERR {type(exc).__name__}: {exc}\n"
            try:
                self.request.sendall(err.encode("utf-8"))
            except Exception:
                pass
            print(f"[receive:error] {peer}: {err.strip()}", flush=True)


class ThreadingVideoTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass, save_dir: Path, display_queue: queue.Queue | None = None):
        self.save_dir = save_dir
        self.display_queue = display_queue
        super().__init__(server_address, RequestHandlerClass)


class VideoHttpHandler(BaseHTTPRequestHandler):
    server_version = "SmartFarmVisionHTTP/0.2"

    @property
    def save_dir(self) -> Path:
        return self.server.save_dir  # type: ignore[attr-defined]

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib method name
        print(f"[http] {self.address_string()} - {format % args}", flush=True)

    def send_bytes(self, data: bytes, content_type: str = "application/octet-stream", status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def latest_marker(self) -> dict[str, Any] | None:
        marker_path = self.save_dir / "latest.json"
        if not marker_path.exists():
            return None
        return json.loads(marker_path.read_text(encoding="utf-8"))

    def latest_file(self) -> Path | None:
        marker = self.latest_marker()
        if not marker:
            return None
        candidate = self.save_dir / Path(marker.get("latest_file", "")).name
        return candidate if candidate.exists() else None

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self.render_index()
        elif path == "/metadata":
            marker = self.latest_marker() or {"message": "no video received yet"}
            self.send_bytes(json.dumps(marker, ensure_ascii=False, indent=2).encode("utf-8"), "application/json; charset=utf-8")
        elif path == "/latest":
            self.send_video(self.latest_file())
        elif path.startswith("/files/"):
            name = Path(unquote(path[len("/files/"):])).name
            self.send_video(self.save_dir / name)
        else:
            self.send_error(404, "not found")

    def render_index(self) -> None:
        files = sorted([p for p in self.save_dir.iterdir() if p.is_file() and not p.name.endswith(".json")], reverse=True)
        latest = self.latest_marker()
        rows = []
        for p in files[:30]:
            rows.append(
                f'<li><a href="/files/{quote(p.name)}">{html.escape(p.name)}</a> '
                f'({p.stat().st_size:,} bytes)</li>'
            )
        latest_info = html.escape(json.dumps(latest, ensure_ascii=False, indent=2)) if latest else "아직 수신된 영상 없음"
        body = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>SmartFarm Vision Video Receiver</title>
<style>body{{font-family:sans-serif;max-width:900px;margin:2rem auto;line-height:1.5}} pre{{background:#f5f5f5;padding:1rem;overflow:auto}}</style>
</head><body>
<h1>SmartFarm Vision Video Receiver</h1>
<p><a href="/latest">latest 영상 다운로드/송출</a> · <a href="/metadata">latest metadata</a></p>
<pre>{latest_info}</pre>
<h2>수신 파일</h2><ul>{''.join(rows) or '<li>없음</li>'}</ul>
</body></html>"""
        self.send_bytes(body.encode("utf-8"), "text/html; charset=utf-8")

    def send_video(self, file_path: Path | None) -> None:
        if file_path is None or not file_path.exists() or not file_path.is_file():
            self.send_error(404, "video not found")
            return
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        if file_path.suffix == ".h264":
            content_type = "video/h264"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(file_path.stat().st_size))
        self.send_header("Content-Disposition", f'inline; filename="{file_path.name}"')
        self.end_headers()
        with file_path.open("rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                self.wfile.write(chunk)


class ThreadingVideoHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address, RequestHandlerClass, save_dir: Path):
        self.save_dir = save_dir
        super().__init__(server_address, RequestHandlerClass)


def run(args: argparse.Namespace) -> None:
    save_dir = Path(args.save_dir).expanduser().resolve()
    save_dir.mkdir(parents=True, exist_ok=True)

    display_queue: queue.Queue[object] | None = None
    display_thread: threading.Thread | None = None
    if args.show_window:
        try:
            import cv2  # type: ignore[import-not-found]  # noqa: F401
        except Exception as exc:
            raise RuntimeError(
                "OpenCV is not available. Activate the local venv first: "
                "source .venv/bin/activate"
            ) from exc
        display_queue = queue.Queue()
        display_thread = start_display_worker(display_queue)

    tcp_server = ThreadingVideoTCPServer((args.host, args.transfer_port), VideoReceiveHandler, save_dir, display_queue=display_queue)
    tcp_thread = threading.Thread(target=tcp_server.serve_forever, name="video-transfer-server", daemon=True)
    tcp_thread.start()
    print(f"[receive] listening on {args.host}:{args.transfer_port}, save_dir={save_dir}", flush=True)

    http_server = None
    if not args.no_http:
        http_server = ThreadingVideoHTTPServer((args.host, args.http_port), VideoHttpHandler, save_dir)
        print(f"[http] serving on http://{args.host}:{args.http_port}/", flush=True)
    if args.show_window:
        print("[display] enabled via OpenCV imshow", flush=True)

    try:
        if http_server:
            http_server.serve_forever()
        else:
            tcp_thread.join()
    except KeyboardInterrupt:
        print("\n[shutdown] stopping servers", flush=True)
    finally:
        tcp_server.shutdown()
        tcp_server.server_close()
        if http_server:
            http_server.shutdown()
            http_server.server_close()
        if display_queue is not None:
            display_queue.put(None)
        if display_thread is not None:
            display_thread.join(timeout=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Receive Raspberry Pi camera videos over socket and optionally display them with OpenCV.")
    parser.add_argument("--host", default="0.0.0.0", help="listen host")
    parser.add_argument("--transfer-port", type=int, default=5001, help="raw TCP receive port")
    parser.add_argument("--http-port", type=int, default=8000, help="HTTP video serving port")
    parser.add_argument("--save-dir", default="incoming_videos", help="directory for received videos")
    parser.add_argument("--no-http", action="store_true", help="only receive files; do not start HTTP server")
    parser.add_argument("--show-window", action="store_true", help="play each received clip with OpenCV imshow")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())

from __future__ import annotations

import json
import socket
import sys
import threading
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "dobot_control_pkg"
sys.path.insert(0, str(PACKAGE_DIR.parent))


def test_vision_capture_client_sends_request_and_reads_json_response():
    from dobot_control_pkg.vision_capture_client import VisionCaptureClient

    received: dict[str, object] = {}
    ready = threading.Event()

    def server() -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", 0))
            received["port"] = sock.getsockname()[1]
            sock.listen(1)
            ready.set()
            conn, _ = sock.accept()
            with conn:
                line = conn.makefile("rb").readline()
                request = json.loads(line.decode("utf-8"))
                received["request"] = request
                response = {
                    "status": "ok",
                    "quality_status": "normal",
                    "saved_path": "/tmp/angle_000.jpg",
                    "angle_deg": request["angle_deg"],
                    "harvest_index": request["harvest_index"],
                }
                conn.sendall((json.dumps(response) + "\n").encode("utf-8"))

    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    assert ready.wait(2)

    port = int(received["port"])
    client = VisionCaptureClient("127.0.0.1", port, timeout_sec=2.0)
    result = client.capture(
        sequence_id="harvest_1_test",
        harvest_index=1,
        angle_deg=0.0,
        width=1280,
        height=720,
        quality=90,
        camera_timeout_ms=800,
    )
    thread.join(2)

    assert received["request"] == {
        "type": "capture",
        "sequence_id": "harvest_1_test",
        "harvest_index": 1,
        "angle_deg": 0.0,
        "width": 1280,
        "height": 720,
        "quality": 90,
        "timeout_ms": 800,
    }
    assert result.quality_status == "normal"
    assert result.saved_path == "/tmp/angle_000.jpg"

from __future__ import annotations

import importlib.util
from pathlib import Path


def load_daemon_module():
    module_path = Path(__file__).with_name("vision_capture_daemon.py")
    spec = importlib.util.spec_from_file_location("vision_capture_daemon", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_save_capture_result_uses_sequence_directory_and_returns_normal_verdict(tmp_path):
    daemon = load_daemon_module()
    request = {
        "type": "capture",
        "sequence_id": "harvest_1_test",
        "harvest_index": 1,
        "angle_deg": -120,
    }
    pi_metadata = {
        "status": "ok",
        "request_id": "req_test",
        "sender": "raspberry-pi5",
        "payload_bytes": 12,
    }

    response = daemon.save_capture_result(tmp_path, request, pi_metadata, b"fake-jpg-data")

    saved_path = Path(response["saved_path"])
    assert response["status"] == "ok"
    assert response["quality_status"] == "normal"
    assert response["harvest_index"] == 1
    assert response["angle_deg"] == -120
    assert saved_path == tmp_path / "harvest_1_test" / "angle_-120.jpg"
    assert saved_path.read_bytes() == b"fake-jpg-data"
    assert (tmp_path / "harvest_1_test" / "capture_session.json").exists()

#!/usr/bin/env python3
"""Thin client for the YOLO inference server.

Used by vision_capture_daemon (지웅) to request quality inspection
after 3 images have been captured and saved locally.
"""

from __future__ import annotations

import json
import socket


class InferenceError(RuntimeError):
    pass


def request_inference(
    image_paths: list[str],
    sequence_id: str = "",
    host: str = "127.0.0.1",
    port: int = 5020,
    timeout_sec: float = 30.0,
) -> str:
    """Send 3 image paths to the inference server and return quality_status.

    Returns:
        "normal" or "error"
    Raises:
        InferenceError on connection failure or bad response.
    """
    request = {
        "type": "infer",
        "sequence_id": sequence_id,
        "image_paths": image_paths,
    }
    try:
        with socket.create_connection((host, port), timeout=timeout_sec) as sock:
            sock.sendall((json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8"))
            line = sock.makefile("rb").readline()
    except OSError as exc:
        raise InferenceError(f"inference server connection failed: {exc}") from exc

    if not line:
        raise InferenceError("inference server closed without response")

    response = json.loads(line.decode("utf-8"))
    if response.get("status") != "ok":
        raise InferenceError(f"inference server error: {response.get('message')}")

    quality = str(response.get("quality_status", "unknown"))
    return quality

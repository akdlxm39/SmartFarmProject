#!/usr/bin/env python3
"""Tiny local client used by Dobot motion code to request vision captures."""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from typing import Any


class VisionCaptureError(RuntimeError):
    """Raised when the local vision capture daemon cannot provide a valid capture."""


@dataclass(frozen=True)
class CaptureResult:
    status: str
    quality_status: str
    saved_path: str
    angle_deg: float
    harvest_index: int
    payload_bytes: int = 0
    request_id: str = ""
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_response(cls, response: dict[str, Any]) -> "CaptureResult":
        if response.get("status") != "ok":
            message = response.get("message") or f"capture failed: {response}"
            raise VisionCaptureError(str(message))
        return cls(
            status=str(response.get("status", "ok")),
            quality_status=str(response.get("quality_status", "unknown")),
            saved_path=str(response.get("saved_path", "")),
            angle_deg=float(response.get("angle_deg", 0.0)),
            harvest_index=int(response.get("harvest_index", 0)),
            payload_bytes=int(response.get("payload_bytes", 0)),
            request_id=str(response.get("request_id", "")),
            metadata=response.get("metadata") if isinstance(response.get("metadata"), dict) else None,
        )


class VisionCaptureClient:
    """Connect to the local PC vision daemon and request one capture."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5012, timeout_sec: float = 10.0) -> None:
        self.host = host
        self.port = int(port)
        self.timeout_sec = float(timeout_sec)

    def capture(
        self,
        *,
        sequence_id: str,
        harvest_index: int,
        angle_deg: float,
        width: int = 1280,
        height: int = 720,
        quality: int = 90,
        camera_timeout_ms: int = 800,
    ) -> CaptureResult:
        request = {
            "type": "capture",
            "sequence_id": sequence_id,
            "harvest_index": int(harvest_index),
            "angle_deg": float(angle_deg),
            "width": int(width),
            "height": int(height),
            "quality": int(quality),
            "timeout_ms": int(camera_timeout_ms),
        }
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout_sec) as sock:
                sock.settimeout(self.timeout_sec)
                sock.sendall((json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8"))
                line = sock.makefile("rb").readline()
        except OSError as exc:
            raise VisionCaptureError(f"vision capture daemon connection failed: {exc}") from exc

        if not line:
            raise VisionCaptureError("vision capture daemon closed without response")
        response = json.loads(line.decode("utf-8"))
        return CaptureResult.from_response(response)

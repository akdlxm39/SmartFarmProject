#!/usr/bin/env python3
"""Shared socket helpers for SmartFarm request/response JPG capture."""

from __future__ import annotations

import json
import socket
import struct
from typing import Any

MAGIC = b"SFJ1"
HEADER_STRUCT = struct.Struct("!4sIQ")
CHUNK_SIZE = 1024 * 1024


def recv_exact(sock: socket.socket, size: int) -> bytes:
    """Receive exactly size bytes or raise if the peer closes early."""
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(min(CHUNK_SIZE, size - len(data)))
        if not chunk:
            raise ConnectionError(f"socket closed while receiving {size} bytes")
        data.extend(chunk)
    return bytes(data)


def send_json_line(sock: socket.socket, message: dict[str, Any]) -> None:
    """Send one UTF-8 JSON object terminated by a newline."""
    sock.sendall((json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8"))


def read_json_line(sock_file: Any) -> dict[str, Any] | None:
    """Read one newline-delimited JSON object from a binary socket file."""
    line = sock_file.readline()
    if not line:
        return None
    return json.loads(line.decode("utf-8"))


def read_jpeg_packet(sock: socket.socket) -> tuple[dict[str, Any], bytes]:
    """Read the SFJ1 metadata+JPEG packet used by the Raspberry Pi client."""
    header = recv_exact(sock, HEADER_STRUCT.size)
    magic, metadata_len, payload_len = HEADER_STRUCT.unpack(header)
    if magic != MAGIC:
        raise ValueError(f"bad magic {magic!r}; expected {MAGIC!r}")
    if metadata_len > 1024 * 1024:
        raise ValueError(f"metadata too large: {metadata_len}")
    metadata = json.loads(recv_exact(sock, metadata_len).decode("utf-8"))
    payload = recv_exact(sock, payload_len)
    return metadata, payload


def write_jpeg_packet(sock: socket.socket, metadata: dict[str, Any], payload: bytes) -> None:
    """Write an SFJ1 metadata+JPEG packet."""
    metadata_bytes = json.dumps(metadata, ensure_ascii=False).encode("utf-8")
    header = HEADER_STRUCT.pack(MAGIC, len(metadata_bytes), len(payload))
    sock.sendall(header)
    sock.sendall(metadata_bytes)
    sock.sendall(payload)

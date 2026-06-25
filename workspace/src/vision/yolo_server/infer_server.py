#!/usr/bin/env python3
"""YOLO inference server.

Receives 3 JPEG images from vision_capture_daemon via TCP socket,
runs YOLOv8 segmentation inference on each image, and returns a
quality verdict: "error" if any image contains an error detection,
"normal" otherwise.

Protocol (control socket, port 5020):
  Request  (JSON line):
    {"type": "infer", "sequence_id": "...", "image_paths": ["path1", "path2", "path3"]}
  Response (JSON line):
    {"status": "ok",    "quality_status": "normal"|"error", "details": [...]}
    {"status": "error", "message": "..."}
"""

from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path

from ultralytics import YOLO


def load_model(model_path: str) -> YOLO:
    return YOLO(model_path)


def infer_images(model: YOLO, image_paths: list[str], conf_threshold: float) -> dict:
    details = []
    has_error = False

    for path in image_paths:
        p = Path(path)
        if not p.exists():
            return {"status": "error", "message": f"image not found: {path}"}

        results = model(str(p), conf=conf_threshold, verbose=False)
        result = results[0]

        detected_labels = []
        if result.boxes is not None and len(result.boxes) > 0:
            for cls_id in result.boxes.cls.tolist():
                label = model.names[int(cls_id)]
                detected_labels.append(label)
                if label == "error":
                    has_error = True

        details.append({"path": str(p), "detected": detected_labels})

    return {
        "status": "ok",
        "quality_status": "error" if has_error else "normal",
        "details": details,
    }


def handle_client(conn: socket.socket, model: YOLO, conf_threshold: float) -> None:
    with conn:
        try:
            line = conn.makefile("rb").readline()
            if not line:
                return
            request = json.loads(line.decode("utf-8"))

            if request.get("type") != "infer":
                resp = {"status": "error", "message": f"unsupported type: {request.get('type')}"}
                conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
                return

            image_paths = request.get("image_paths", [])
            if len(image_paths) != 3:
                resp = {"status": "error", "message": f"expected 3 image_paths, got {len(image_paths)}"}
                conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
                return

            print(f"[infer] sequence={request.get('sequence_id')} paths={image_paths}", flush=True)
            response = infer_images(model, image_paths, conf_threshold)
            print(f"[infer] result={response['quality_status']} details={response.get('details')}", flush=True)
            conn.sendall((json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8"))

        except Exception as exc:
            try:
                resp = {"status": "error", "message": str(exc)}
                conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
            except OSError:
                pass
            print(f"[infer:error] {exc}", flush=True)


def run(args: argparse.Namespace) -> None:
    model = load_model(args.model)
    print(f"[infer] model loaded: {args.model}, names={model.names}", flush=True)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((args.host, args.port))
        server.listen(8)
        print(f"[infer] listening on {args.host}:{args.port}", flush=True)
        while True:
            conn, peer = server.accept()
            print(f"[infer] connection from {peer[0]}:{peer[1]}", flush=True)
            handle_client(conn, model, args.conf)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YOLO inference server for SmartFarm quality inspection.")
    parser.add_argument("--model", default="best.pt", help="Path to YOLO .pt model file")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=5020, help="Bind port")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    return parser.parse_args(argv)


if __name__ == "__main__":
    run(parse_args())

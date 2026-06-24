#!/bin/bash
# Run the YOLO inference server inside the local venv.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source .venv/bin/activate
exec python infer_server.py \
  --model best.pt \
  --host 127.0.0.1 \
  --port 5020 \
  --conf 0.25 \
  "$@"

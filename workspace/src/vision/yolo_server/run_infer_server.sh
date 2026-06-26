#!/bin/bash
# Run the YOLO inference server. Uses local .venv if present.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
MODEL_PATH="${MODEL_PATH:-$SCRIPT_DIR/../../data/models/best.pt}"
exec python infer_server.py \
  --model "$MODEL_PATH" \
  --host 127.0.0.1 \
  --port 5020 \
  --conf 0.25 \
  "$@"

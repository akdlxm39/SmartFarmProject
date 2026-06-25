#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
source .venv/bin/activate

python vision_capture_daemon.py \
  --pi-host 0.0.0.0 \
  --pi-port 5002 \
  --control-host 127.0.0.1 \
  --control-port 5012 \
  --save-dir incoming_jpegs

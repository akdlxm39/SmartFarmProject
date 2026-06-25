#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
source .venv/bin/activate
rm -rf incoming_jpegs_smoke smoke_tmp_jpeg
mkdir -p smoke_tmp_jpeg

MOCK_JPG="smoke_tmp_jpeg/mock_frame.jpg"
python - <<'PY'
from pathlib import Path
import cv2
import numpy as np
img = np.zeros((240, 320, 3), dtype=np.uint8)
img[:] = (30, 80, 130)
cv2.putText(img, 'SmartFarm JPG Mock', (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
cv2.imwrite('smoke_tmp_jpeg/mock_frame.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
PY

python pc_jpeg_capture_server.py \
  --host 127.0.0.1 \
  --port 5012 \
  --save-dir incoming_jpegs_smoke \
  --auto-capture \
  --count 1 > smoke_tmp_jpeg/server.log 2>&1 &
SERVER_PID=$!
cleanup() {
  kill "$SERVER_PID" >/dev/null 2>&1 || true
  wait "$SERVER_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

python - <<'PY'
import socket, time
for _ in range(50):
    try:
        with socket.create_connection(('127.0.0.1', 5012), timeout=0.2):
            pass
    except Exception:
        time.sleep(0.1)
    else:
        # The first connect may consume the one server accept, so do not use this readiness path.
        break
PY
# Restart server because readiness probe connects to the single-client server.
kill "$SERVER_PID" >/dev/null 2>&1 || true
wait "$SERVER_PID" >/dev/null 2>&1 || true
python pc_jpeg_capture_server.py \
  --host 127.0.0.1 \
  --port 5012 \
  --save-dir incoming_jpegs_smoke \
  --auto-capture \
  --count 1 > smoke_tmp_jpeg/server.log 2>&1 &
SERVER_PID=$!
sleep 0.3

python raspi_jpeg_capture_client.py \
  --server-host 127.0.0.1 \
  --server-port 5012 \
  --mock-source "$MOCK_JPG"
wait "$SERVER_PID"
trap - EXIT

python - <<'PY'
import json
from pathlib import Path
import cv2
marker = Path('incoming_jpegs_smoke/latest_jpeg.json')
assert marker.exists(), 'latest_jpeg.json missing'
data = json.loads(marker.read_text(encoding='utf-8'))
img_path = Path(data['latest_path'])
assert img_path.exists(), f'JPG missing: {img_path}'
img = cv2.imread(str(img_path))
assert img is not None, f'OpenCV could not decode {img_path}'
print(f"[ok] received JPG {img_path} shape={img.shape} bytes={img_path.stat().st_size}")
PY

#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
rm -rf incoming_videos smoke_tmp
mkdir -p smoke_tmp

TEST_VIDEO="smoke_tmp/test_video.mp4"
if command -v ffmpeg >/dev/null 2>&1; then
  ffmpeg -y -hide_banner -loglevel error \
    -f lavfi -i testsrc=size=320x240:rate=10 \
    -t 1 \
    -pix_fmt yuv420p \
    "$TEST_VIDEO"
else
  # Protocol-only fallback when ffmpeg is not available.
  python3 - <<'PY'
from pathlib import Path
Path('smoke_tmp/test_video.mp4').write_bytes(b'SMARTFARM_TEST_VIDEO_BYTES' * 1024)
PY
fi

python3 pc_receiver_streamer.py \
  --host 127.0.0.1 \
  --transfer-port 5001 \
  --http-port 8000 \
  --save-dir incoming_videos > smoke_tmp/server.log 2>&1 &
SERVER_PID=$!
cleanup() {
  kill "$SERVER_PID" >/dev/null 2>&1 || true
  wait "$SERVER_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Wait for TCP/HTTP server startup.
python3 - <<'PY'
import socket, time
for _ in range(50):
    try:
        with socket.create_connection(('127.0.0.1', 5001), timeout=0.2):
            pass
    except Exception:
        time.sleep(0.1)
    else:
        break
else:
    raise SystemExit('receiver did not start')
PY

python3 raspi_capture_send.py \
  --pc-host 127.0.0.1 \
  --pc-port 5001 \
  --mock-source "$TEST_VIDEO"

python3 - <<'PY'
import json
from pathlib import Path
marker = Path('incoming_videos/latest.json')
assert marker.exists(), 'latest.json was not created'
data = json.loads(marker.read_text(encoding='utf-8'))
latest = Path(data['latest_path'])
assert latest.exists(), f'latest file not found: {latest}'
assert latest.stat().st_size > 0, 'latest file is empty'
print(f"[ok] received {latest} ({latest.stat().st_size} bytes)")
PY

python3 - <<'PY'
from urllib.request import urlopen
with urlopen('http://127.0.0.1:8000/metadata', timeout=3) as r:
    body = r.read().decode('utf-8')
assert 'latest_file' in body, body
print('[ok] http metadata endpoint responded')
PY

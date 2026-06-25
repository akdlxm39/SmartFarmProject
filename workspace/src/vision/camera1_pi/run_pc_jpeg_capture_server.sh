#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
source .venv/bin/activate

CV2_QT_DIR="$(python - <<'PY'
import cv2, pathlib
print(pathlib.Path(cv2.__file__).resolve().parent / 'qt')
PY
)"
FONT_SRC_DIR="/usr/share/fonts/truetype/dejavu"
FONT_DST_DIR="${CV2_QT_DIR}/fonts"

if [ -d "$FONT_SRC_DIR" ] && [ ! -e "$FONT_DST_DIR" ]; then
  mkdir -p "$CV2_QT_DIR"
  ln -s "$FONT_SRC_DIR" "$FONT_DST_DIR"
fi

export QT_QPA_FONTDIR="${QT_QPA_FONTDIR:-$FONT_SRC_DIR}"

exec python pc_jpeg_capture_server.py \
  --host 0.0.0.0 \
  --port 5002 \
  --save-dir incoming_jpegs \
  --width 1280 \
  --height 720 \
  --quality 90 \
  --show-window

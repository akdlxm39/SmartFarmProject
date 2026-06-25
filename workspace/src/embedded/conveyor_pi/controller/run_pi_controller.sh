#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ -d .venv ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

needs_gpio=1
for arg in "$@"; do
  if [ "$arg" = "--dry-run-motor" ]; then
    needs_gpio=0
  fi
done

if [ "$needs_gpio" -eq 1 ]; then
  python3 - <<'PY'
import sys
try:
    import gpiod
except ModuleNotFoundError:
    print("ERROR: Python gpiod binding is missing.", file=sys.stderr)
    print("Install on Raspberry Pi:", file=sys.stderr)
    print("  sudo apt update && sudo apt install -y gpiod python3-libgpiod", file=sys.stderr)
    print("  rm -rf .venv && python3 -m venv --system-site-packages .venv", file=sys.stderr)
    print("  source .venv/bin/activate && python -m pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)
if not hasattr(gpiod.Chip, "get_line"):
    print("ERROR: imported gpiod does not expose libgpiod v1 Chip.get_line API.", file=sys.stderr)
    print("Use OS package python3-libgpiod with a --system-site-packages venv; do not use an incompatible PyPI gpiod v2 binding.", file=sys.stderr)
    sys.exit(1)
PY
fi

exec python3 conveyor_modbus_client_controller.py \
  --server-host 192.168.110.109 \
  --server-port 50200 \
  --device-id 1 \
  "$@"

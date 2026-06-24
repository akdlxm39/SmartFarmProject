#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ -d .venv ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
exec python3 conveyor_modbus_client_controller.py \
  --server-host 192.168.110.109 \
  --server-port 50200 \
  --device-id 1 \
  "$@"

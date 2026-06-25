#!/usr/bin/env bash
set -eo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh
MAP_BASENAME="${1:-map/pjt_map_new}"
mkdir -p "$(dirname "$MAP_BASENAME")"
ABS_BASENAME="$(python3 -c 'import os,sys; print(os.path.abspath(sys.argv[1]))' "$MAP_BASENAME")"
echo "Saving map to ${ABS_BASENAME}.yaml / ${ABS_BASENAME}.pgm"
exec ros2 run nav2_map_server map_saver_cli -f "$ABS_BASENAME"

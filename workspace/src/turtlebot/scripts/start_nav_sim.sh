#!/usr/bin/env bash
set -eo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh
MAP_FILE="${1:-map/pjt_map.yaml}"
ABS_MAP="$(python3 -c 'import os,sys; print(os.path.abspath(sys.argv[1]))' "$MAP_FILE")"
if [ ! -f "$ABS_MAP" ]; then
  echo "Map yaml not found: $ABS_MAP" >&2
  exit 2
fi
exec ros2 launch turtlebot3_navigation2 navigation2.launch.py use_sim_time:=true map:="$ABS_MAP"

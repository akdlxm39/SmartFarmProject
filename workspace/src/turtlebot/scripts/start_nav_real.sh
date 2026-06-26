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

# nav2_map_server can mis-handle non-ASCII paths on this setup
# (e.g. 지웅 becomes uC9C0uC6C5), so run map loading from an ASCII-safe mirror.
if python3 -c 'import sys; sys.exit(0 if sys.argv[1].isascii() else 1)' "$ABS_MAP"; then
  NAV_MAP="$ABS_MAP"
else
  SAFE_MAP_DIR="${SMARTFARM_TURTLEBOT_SAFE_MAP_DIR:-/tmp/smartfarm_turtlebot_nav_map}"
  mkdir -p "$SAFE_MAP_DIR"
  cp "$(dirname "$ABS_MAP")"/* "$SAFE_MAP_DIR"/
  NAV_MAP="$SAFE_MAP_DIR/$(basename "$ABS_MAP")"
  echo "Using ASCII-safe map mirror: $NAV_MAP"
fi

echo "Launching Navigation2 with map: $NAV_MAP"
exec ros2 launch turtlebot3_navigation2 navigation2.launch.py map:="$NAV_MAP"

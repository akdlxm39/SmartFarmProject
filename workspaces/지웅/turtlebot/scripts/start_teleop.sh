#!/usr/bin/env bash
set -eo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh
exec ros2 run turtlebot3_teleop teleop_keyboard

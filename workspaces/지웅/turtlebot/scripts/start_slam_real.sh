#!/usr/bin/env bash
set -eo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh
exec ros2 launch turtlebot3_cartographer cartographer.launch.py

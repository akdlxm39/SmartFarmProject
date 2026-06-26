#!/usr/bin/env bash
set -eo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh

echo "== ROS topics visible from Remote PC =="
ros2 topic list | sort

echo
for topic in /scan /odom /imu /battery_state /cmd_vel /tf; do
  if ros2 topic list | grep -qx "$topic"; then
    echo "OK: $topic"
  else
    echo "MISSING: $topic"
  fi
done

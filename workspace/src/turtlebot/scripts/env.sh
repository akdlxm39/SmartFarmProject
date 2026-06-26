#!/usr/bin/env bash
# Shared environment for SmartFarmProject TurtleBot work.
# This file is meant to be sourced, so it intentionally does not enable set -e/-u.

export TURTLEBOT3_MODEL="${TURTLEBOT3_MODEL:-waffle_pi}"
# Actual TurtleBot SBC check showed ROS_DOMAIN_ID=32.
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-32}"

# ROS setup scripts may reference unset variables internally.
source /opt/ros/humble/setup.bash

if [ -f /home/ssafy/ros2/turtlebot3_ws/install/setup.bash ]; then
  source /home/ssafy/ros2/turtlebot3_ws/install/setup.bash
fi

WORKSPACE_DIR="/home/ssafy/work/SmartFarmProject/workspaces/지웅/turtlebot/ros2_ws"
if [ -f "$WORKSPACE_DIR/install/setup.bash" ]; then
  source "$WORKSPACE_DIR/install/setup.bash"
fi

echo "TURTLEBOT3_MODEL=$TURTLEBOT3_MODEL"
echo "ROS_DOMAIN_ID=$ROS_DOMAIN_ID"

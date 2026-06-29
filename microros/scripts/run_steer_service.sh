#!/bin/bash
# Wrapper para systemd: nodo de servos de dirección.
set -euo pipefail

export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
source /opt/ros/jazzy/setup.bash
source /home/computer/OUTDOOR_ROBOT/install/setup.bash

exec ros2 run bot_control steer_servo_node --ros-args \
  --params-file /home/computer/OUTDOOR_ROBOT/src/bot_control/config/steer_servo.yaml

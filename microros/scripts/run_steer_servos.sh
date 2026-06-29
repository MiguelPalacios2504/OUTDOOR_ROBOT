#!/bin/bash
# Nodo de dirección: /hw/joint_commands[0..3] -> servos STS en la placa serial de la Pi
set -eo pipefail

sudo systemctl stop outdoor-robot-steer.service 2>/dev/null || true

export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
source /opt/ros/jazzy/setup.bash
source /home/computer/OUTDOOR_ROBOT/install/setup.bash

echo "Servos ST/SC en bus serial. Puerto: /dev/ttyACM0 (ajusta steer_servo.yaml)"
echo ""

exec ros2 run bot_control steer_servo_node --ros-args \
  --params-file /home/computer/OUTDOOR_ROBOT/src/bot_control/config/steer_servo.yaml

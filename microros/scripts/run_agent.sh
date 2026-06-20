#!/bin/bash
# Arranca el micro-ROS agent (serial). Dejar corriendo en terminal 1.
# Uso: ~/OUTDOOR_ROBOT/microros/scripts/run_agent.sh [/dev/ttyUSB0]
set -e

SERIAL="${1:-/dev/ttyUSB0}"

sudo systemctl stop robot_bringup.service 2>/dev/null || true
pkill -f micro_ros_agent 2>/dev/null || true
sleep 1

export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
source /opt/ros/jazzy/setup.bash
[[ -f /home/computer/uros_ws/install/setup.bash ]] && source /home/computer/uros_ws/install/setup.bash

echo "Arrancando agent en $SERIAL ..."
echo "Cuando veas create_publisher / create_subscription, el ESP32 está conectado."
echo "Si no aparecen topics, pulsa RESET en el ESP32."
echo ""

exec ros2 run micro_ros_agent micro_ros_agent serial --dev "$SERIAL" -b 115200 -v6

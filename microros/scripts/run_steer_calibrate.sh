#!/bin/bash
# Calibración manual servos dirección (mover a mano, registrar rango)
set -eo pipefail

export ROS_DOMAIN_ID=0
source /opt/ros/jazzy/setup.bash
source /home/computer/OUTDOOR_ROBOT/install/setup.bash

MODE="${1:-explore}"

echo "Modos:"
echo "  explore    — torque OFF, mueve libre y ve ticks en vivo"
echo "  calibrate  — un servo a la vez, registra min/max/centro"
echo ""
echo "Usando modo: $MODE"
echo ""

exec ros2 run bot_control steer_servo_calibrate -- "$MODE"

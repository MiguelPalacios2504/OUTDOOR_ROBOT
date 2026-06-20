#!/bin/bash
# Arranca micro-ROS en la Pi (agent + reset ESP32 opcional).
# Uso: ~/OUTDOOR_ROBOT/microros/scripts/start_microros_pi.sh [/dev/ttyUSB0]
set -e

SERIAL_DEV="${1:-/dev/ttyUSB0}"

if [[ ! -e "$SERIAL_DEV" ]]; then
  echo "No existe $SERIAL_DEV — conecta el ESP32 e inténtalo de nuevo."
  exit 1
fi

sudo systemctl stop robot_bringup.service 2>/dev/null || true

export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp

source /opt/ros/jazzy/setup.bash
[[ -f /home/computer/uros_ws/install/setup.bash ]] && source /home/computer/uros_ws/install/setup.bash

echo "Dominio ROS: $ROS_DOMAIN_ID"
echo "Puerto: $SERIAL_DEV"
echo ""
echo "Orden: 1) agent arranca  2) reset ESP32  3) espera create_publisher"
echo ""

ros2 daemon stop 2>/dev/null || true
ros2 daemon start

ros2 run micro_ros_agent micro_ros_agent serial --dev "$SERIAL_DEV" -b 115200 -v6 &
AGENT_PID=$!

sleep 2

python3 - <<PY 2>/dev/null || true
import time
try:
    import serial
    s = serial.Serial("${SERIAL_DEV}", 115200)
    s.dtr = False
    time.sleep(0.1)
    s.dtr = True
    s.close()
    print("Reset ESP32 enviado (agent ya corriendo).")
except Exception:
    print("Pulsa RESET en el ESP32 manualmente.")
PY

echo ""
echo "Esperando create_publisher / create_subscription..."
echo ""

wait "$AGENT_PID"

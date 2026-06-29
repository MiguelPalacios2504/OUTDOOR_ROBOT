#!/bin/bash
# Wrapper para systemd: micro-ROS agent + reset ESP32 por DTR.
set -euo pipefail

SERIAL="${1:-/dev/ttyUSB0}"

export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
source /opt/ros/jazzy/setup.bash
[[ -f /home/computer/uros_ws/install/setup.bash ]] && source /home/computer/uros_ws/install/setup.bash

ros2 daemon stop 2>/dev/null || true
ros2 daemon start

python3 - <<PY || true
import time
try:
    import serial
    s = serial.Serial("${SERIAL}", 115200)
    s.dtr = False
    time.sleep(0.1)
    s.dtr = True
    s.close()
except Exception:
    pass
PY

exec ros2 run micro_ros_agent micro_ros_agent serial --dev "$SERIAL" -b 115200

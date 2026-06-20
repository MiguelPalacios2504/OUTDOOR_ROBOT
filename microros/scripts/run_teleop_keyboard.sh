#!/bin/bash
# Teleop por teclado → /cmd_vel → /hw/joint_commands → ESP32
# Terminal 2 (interactiva). Terminal 1 debe tener run_agent.sh corriendo.
set -eo pipefail

if [[ ! -t 0 ]]; then
  echo "ERROR: esta terminal no es interactiva (sin TTY)."
  echo "  Si usas SSH:  ssh -t computer@<ip-de-la-pi>"
  exit 1
fi

export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
source /opt/ros/jazzy/setup.bash
source /home/computer/OUTDOOR_ROBOT/install/setup.bash

echo "Teclas (teleop_twist_keyboard):"
echo "  i = adelante   , = atrás"
echo "  j = girar izq  l = girar der"
echo "  k / espacio = parar"
echo "  q/z = subir/bajar velocidad"
echo ""
echo "Terminal 1: run_agent.sh debe seguir corriendo."
echo ""

cleanup() {
  kill "$BRIDGE_PID" 2>/dev/null || true
  wait "$BRIDGE_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

ros2 run bot_control teleop_joint_commands_node &
BRIDGE_PID=$!
sleep 1

exec ros2 run teleop_twist_keyboard teleop_twist_keyboard

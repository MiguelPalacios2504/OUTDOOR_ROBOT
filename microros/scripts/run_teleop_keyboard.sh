#!/bin/bash
# Teleop por teclado → /cmd_vel → /hw/joint_commands
#   índices 0-3: servos dirección (Pi, run_steer_servos.sh en terminal 2)
#   índices 4-7: motores (ESP32, run_agent.sh en terminal 1)
# Terminal 3 (interactiva). Antes: terminal 1 = agent, terminal 2 = steer servos.
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
echo "Terminal 1: run_agent.sh (motores ESP32)"
echo "Terminal 2: run_steer_servos.sh (dirección — obligatorio)"
echo ""

cleanup() {
  kill "$BRIDGE_PID" 2>/dev/null || true
  kill "$STEER_PID" 2>/dev/null || true
  wait "$BRIDGE_PID" 2>/dev/null || true
  wait "$STEER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

ros2 run bot_control teleop_joint_commands_node --ros-args \
  --params-file /home/computer/OUTDOOR_ROBOT/src/bot_control/config/teleop_joint_commands.yaml &
BRIDGE_PID=$!
sleep 1

# Por defecto NO arranca steer aquí: usar run_steer_servos.sh en otra terminal.
# Para intentar arrancarlo en este script: START_STEER_SERVOS=1 run_teleop_keyboard.sh
if [[ "${START_STEER_SERVOS:-0}" == "1" ]]; then
  ros2 run bot_control steer_servo_node --ros-args \
    --params-file /home/computer/OUTDOOR_ROBOT/src/bot_control/config/steer_servo.yaml &
  STEER_PID=$!
  sleep 1
fi

exec ros2 run teleop_twist_keyboard teleop_twist_keyboard

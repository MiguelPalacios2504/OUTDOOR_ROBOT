#!/bin/bash
# Teleop por joystick → /cmd_vel → /hw/joint_commands
#   índices 0-3: servos dirección (run_steer_servos.sh en terminal 2)
#   índices 4-7: motores (ESP32, run_agent.sh en terminal 1)
# Terminal 3. Antes: terminal 1 = agent, terminal 2 = steer servos.
set -eo pipefail

if [[ ! -e /dev/input/js0 ]]; then
  echo "ERROR: no hay /dev/input/js0."
  echo "  El mando está en USB pero falta el driver. Ejecuta:"
  echo "    sudo ~/OUTDOOR_ROBOT/microros/scripts/setup_joystick.sh"
  echo "  Luego vuelve a lanzar este script."
  exit 1
fi

export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
source /opt/ros/jazzy/setup.bash
source /home/computer/OUTDOOR_ROBOT/install/setup.bash

echo "Joystick (Xbox / genérico):"
echo "  stick izquierdo = avance / giro"
echo "  suelta sticks = parar"
echo ""
echo "Terminal 1: run_agent.sh (motores ESP32)"
echo "Terminal 2: run_steer_servos.sh (dirección — obligatorio)"
echo ""

cleanup() {
  kill "$JOY_PID" "$TELEOP_PID" "$BRIDGE_PID" 2>/dev/null || true
  kill "$STEER_PID" 2>/dev/null || true
  wait "$JOY_PID" "$TELEOP_PID" "$BRIDGE_PID" 2>/dev/null || true
  wait "$STEER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

ros2 run bot_control teleop_joint_commands_node --ros-args \
  --params-file /home/computer/OUTDOOR_ROBOT/src/bot_control/config/teleop_joint_commands.yaml &
BRIDGE_PID=$!
sleep 1

if [[ "${START_STEER_SERVOS:-0}" == "1" ]]; then
  ros2 run bot_control steer_servo_node --ros-args \
    --params-file /home/computer/OUTDOOR_ROBOT/src/bot_control/config/steer_servo.yaml &
  STEER_PID=$!
  sleep 1
fi

ros2 run joy joy_node --ros-args \
  -p autorepeat_rate:=20.0 \
  -p deadzone:=0.15 &
JOY_PID=$!
sleep 1

ros2 run teleop_twist_joy teleop_node --ros-args \
  -p axis_linear.x:=1 \
  -p axis_angular.yaw:=0 \
  -p scale_linear.x:=0.5 \
  -p scale_angular.yaw:=-1.0 \
  -p require_enable_button:=false &
TELEOP_PID=$!

wait "$TELEOP_PID"

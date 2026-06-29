#!/bin/bash
# Instala arranque automático del robot y acceso SSH estable en la Pi.
# Uso: ~/OUTDOOR_ROBOT/microros/scripts/install_pi_setup.sh
set -euo pipefail

ROBOT_HOSTNAME="${ROBOT_HOSTNAME:-outdoor-robot}"
ETH_IP="${ETH_IP:-192.168.3.20/24}"
ETH_GW="${ETH_GW:-192.168.3.1}"
ETH_CON_NAME="${ETH_CON_NAME:-outdoor-robot-eth}"
REPO="/home/computer/OUTDOOR_ROBOT"
SYSTEMD_SRC="$REPO/microros/systemd"
SYSTEMD_DST="/etc/systemd/system"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Ejecuta con sudo:"
  echo "  sudo $REPO/microros/scripts/install_pi_setup.sh"
  exit 1
fi

echo "=== Hostname + mDNS (${ROBOT_HOSTNAME}.local) ==="
hostnamectl set-hostname "$ROBOT_HOSTNAME"
if systemctl is-enabled avahi-daemon >/dev/null 2>&1; then
  systemctl restart avahi-daemon
fi
echo "  SSH: ssh computer@${ROBOT_HOSTNAME}.local"

echo ""
echo "=== Ethernet estática (cable) ${ETH_IP} ==="
"$REPO/microros/scripts/setup_ethernet_static.sh"

echo ""
echo "=== Paquetes ROS joystick (joy) ==="
apt-get install -y ros-jazzy-joy ros-jazzy-teleop-twist-joy

echo ""
echo "=== Scripts ejecutables ==="
chmod +x \
  "$REPO/microros/scripts/wait-for-device.sh" \
  "$REPO/microros/scripts/run_agent_service.sh" \
  "$REPO/microros/scripts/run_steer_service.sh" \
  "$REPO/microros/scripts/run_agent.sh" \
  "$REPO/microros/scripts/run_steer_servos.sh" \
  "$REPO/microros/scripts/run_teleop_keyboard.sh" \
  "$REPO/microros/scripts/run_teleop_joy.sh" \
  "$REPO/microros/scripts/setup_joystick.sh" \
  "$REPO/microros/scripts/setup_ethernet_static.sh"

echo ""
echo "=== Driver joystick Xbox (xpad) ==="
"$REPO/microros/scripts/setup_joystick.sh" || true

echo ""
echo "=== systemd: agent + steer al arranque ==="
cp "$SYSTEMD_SRC/outdoor-robot.target" "$SYSTEMD_DST/"
cp "$SYSTEMD_SRC/outdoor-robot-agent.service" "$SYSTEMD_DST/"
cp "$SYSTEMD_SRC/outdoor-robot-steer.service" "$SYSTEMD_DST/"

systemctl daemon-reload
systemctl disable robot_bringup.service 2>/dev/null || true
systemctl stop robot_bringup.service 2>/dev/null || true
systemctl enable outdoor-robot.target
systemctl enable outdoor-robot-agent.service
systemctl enable outdoor-robot-steer.service

echo ""
echo "=== Iniciando servicios ahora ==="
systemctl restart outdoor-robot-agent.service || true
systemctl restart outdoor-robot-steer.service || true

echo ""
echo "Listo."
echo ""
echo "Conexión desde laptop:"
echo "  WiFi (cualquier red):  ssh computer@${ROBOT_HOSTNAME}.local"
echo "  Ethernet directo:      ssh computer@${ETH_IP%/*}"
echo ""
echo "Tras encender ESP32 + placa servos, agent y steer arrancan solos."
echo "Solo falta teleop (terminal interactiva):"
echo "  ~/OUTDOOR_ROBOT/microros/scripts/run_teleop_joy.sh"
echo "  (o teclado: run_teleop_keyboard.sh)"
echo ""
echo "Estado: systemctl status outdoor-robot-agent outdoor-robot-steer"

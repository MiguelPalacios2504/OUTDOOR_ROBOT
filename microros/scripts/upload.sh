#!/bin/bash
# Sube firmware al ESP32 desde la Pi (PlatformIO).
set -eo pipefail

export PATH="$HOME/.platformio/penv/bin:$HOME/.local/bin:$PATH"
SERIAL="${1:-/dev/ttyUSB0}"
FIRMWARE_DIR="$(cd "$(dirname "$0")/../outdoor_robot" && pwd)"

sudo systemctl stop robot_bringup.service 2>/dev/null || true
pkill -f micro_ros_agent 2>/dev/null || true
sleep 1

if [[ ! -e "$SERIAL" ]]; then
  echo "ERROR: no hay $SERIAL — conecta el ESP32."
  exit 1
fi

cd "$FIRMWARE_DIR"
echo "Compilando y subiendo firmware desde $FIRMWARE_DIR"
echo "(la 1ª vez tarda varios minutos)..."
pio run -e esp32dev -t upload
echo "OK — firmware subido."

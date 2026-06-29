#!/bin/bash
# Espera a que aparezca un dispositivo serial (p. ej. al encender ESP32 o placa servos).
set -euo pipefail

DEV="${1:?usage: wait-for-device.sh /dev/ttyUSB0 [timeout_sec]}"
TIMEOUT="${2:-180}"
ELAPSED=0

while [[ ! -e "$DEV" ]]; do
  if (( ELAPSED >= TIMEOUT )); then
    echo "Timeout esperando $DEV (${TIMEOUT}s)" >&2
    exit 1
  fi
  sleep 2
  ELAPSED=$((ELAPSED + 2))
done

# Estabilizar tras enumeración USB
sleep 1
echo "Dispositivo listo: $DEV"

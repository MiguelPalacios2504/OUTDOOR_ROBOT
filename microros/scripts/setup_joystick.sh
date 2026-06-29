#!/bin/bash
# Carga el driver xpad para mandos Xbox 360 / clones USB.
# Uso:
#   1. Conecta el mando por USB
#   2. sudo ~/OUTDOOR_ROBOT/microros/scripts/setup_joystick.sh
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Ejecuta con sudo:"
  echo "  sudo $0"
  exit 1
fi

find_xbox_usb() {
  local dev vendor product name
  for dev in /sys/bus/usb/devices/*; do
    [[ -f "$dev/idVendor" ]] || continue
    vendor=$(cat "$dev/idVendor")
    [[ "$vendor" == "045e" ]] || continue
    product=$(cat "$dev/idProduct")
    name=$(basename "$dev")
    echo "$name $vendor:$product $(cat "$dev/product" 2>/dev/null || true)"
  done
}

MODULES_FILE=/etc/modules
if ! grep -qx 'xpad' "$MODULES_FILE" 2>/dev/null; then
  echo "xpad" >> "$MODULES_FILE"
  echo "Añadido xpad a $MODULES_FILE (carga automática al boot)."
fi

modprobe xpad
echo "Driver xpad cargado."

xbox_devices=$(find_xbox_usb || true)
if [[ -z "$xbox_devices" ]]; then
  echo ""
  echo "ERROR: no hay ningún mando Xbox conectado por USB."
  echo "  Conecta el mando a un puerto USB de la Pi y vuelve a ejecutar:"
  echo "    sudo $0"
  echo ""
  echo "Dispositivos USB actuales:"
  lsusb
  exit 1
fi

echo "Mando detectado:"
echo "$xbox_devices" | while read -r line; do echo "  $line"; done

bound=0
while read -r name _rest; do
  [[ -n "$name" ]] || continue
  if [[ -e "/sys/bus/usb/drivers/xpad/$name" ]]; then
    echo "  $name ya enlazado a xpad."
    bound=1
    continue
  fi
  if echo "$name" | tee /sys/bus/usb/drivers/xpad/bind >/dev/null 2>&1; then
    echo "  $name enlazado a xpad."
    bound=1
  else
    echo "  AVISO: no se pudo enlazar $name (prueba otro puerto USB)."
  fi
done <<< "$xbox_devices"

sleep 0.5
if [[ -e /dev/input/js0 ]]; then
  echo ""
  echo "OK: /dev/input/js0 listo."
  ls -la /dev/input/js0
  echo ""
  echo "Ahora ejecuta (sin sudo):"
  echo "  ~/OUTDOOR_ROBOT/microros/scripts/run_teleop_joy.sh"
else
  echo ""
  echo "Mando en USB pero sin /dev/input/js0."
  echo "Prueba:"
  echo "  1. Otro puerto USB de la Pi"
  echo "  2. Desconectar y reconectar el cable"
  echo "  3. Volver a ejecutar: sudo $0"
  echo ""
  journalctl -k -n 15 --no-pager 2>/dev/null | grep -iE 'xpad|xbox|input|usb 004' || true
  exit 1
fi

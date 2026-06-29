#!/bin/bash
# IP fija por cable ethernet en eth0 (conexión directa Pi <-> laptop).
# Uso:
#   sudo ~/OUTDOOR_ROBOT/microros/scripts/setup_ethernet_static.sh
#
# En la laptop (cable directo), configura manualmente:
#   IP: 192.168.3.1   Máscara: 255.255.255.0
# Luego: ssh computer@192.168.3.20
set -euo pipefail

ETH_IP="${ETH_IP:-192.168.3.20/24}"
ETH_GW="${ETH_GW:-192.168.3.1}"
ETH_CON_NAME="${ETH_CON_NAME:-outdoor-robot-eth}"
NETPLAN_FILE="/etc/netplan/99-outdoor-robot-eth.yaml"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Ejecuta con sudo:"
  echo "  sudo $0"
  exit 1
fi

if ! command -v nmcli >/dev/null 2>&1; then
  echo "ERROR: nmcli no encontrado (NetworkManager)."
  exit 1
fi

if ! nmcli device status | grep -q '^eth0'; then
  echo "ERROR: no hay interfaz eth0."
  exit 1
fi

# La Pi suele traer netplan-eth0 con DHCP; eso se queda en "activating" sin router.
EXISTING_CON=$(nmcli -t -f NAME,DEVICE connection show | awk -F: '$2=="eth0"{print $1; exit}')
if [[ -z "$EXISTING_CON" ]]; then
  EXISTING_CON="$ETH_CON_NAME"
  nmcli connection add type ethernet ifname eth0 con-name "$ETH_CON_NAME"
fi

if [[ "$EXISTING_CON" != "$ETH_CON_NAME" ]]; then
  nmcli connection modify "$EXISTING_CON" connection.id "$ETH_CON_NAME" 2>/dev/null || true
fi

nmcli connection modify "$ETH_CON_NAME" \
  connection.interface-name eth0 \
  connection.autoconnect yes \
  connection.autoconnect-priority 100 \
  ipv4.method manual \
  ipv4.addresses "$ETH_IP" \
  ipv4.gateway "$ETH_GW" \
  ipv4.dns "8.8.8.8,1.1.1.1" \
  ipv4.may-fail yes \
  ipv6.method ignore

cat > "$NETPLAN_FILE" <<EOF
# Outdoor robot — IP fija por cable (generado por setup_ethernet_static.sh)
network:
  version: 2
  renderer: NetworkManager
  ethernets:
    eth0:
      dhcp4: false
      addresses:
        - ${ETH_IP}
      routes:
        - to: default
          via: ${ETH_GW}
      optional: true
EOF
chmod 600 "$NETPLAN_FILE"
netplan apply 2>/dev/null || true

nmcli connection down "$ETH_CON_NAME" 2>/dev/null || true
sleep 1
nmcli connection up "$ETH_CON_NAME"

sleep 1
echo ""
echo "=== Ethernet configurado ==="
ip -br addr show eth0
echo ""
echo "Desde la laptop (cable directo):"
echo "  1. IP manual en el adaptador ethernet: ${ETH_GW%/*} / 255.255.255.0"
echo "  2. ssh computer@${ETH_IP%/*}"

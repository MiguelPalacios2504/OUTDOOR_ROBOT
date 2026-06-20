# micro-ROS — troubleshooting (Pi + ESP32)

## Orden de arranque correcto

Usa **dos terminales** (más una tercera opcional para teleop).

**Terminal 1 — agent (dejar corriendo):**

```bash
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
source /opt/ros/jazzy/setup.bash
source ~/uros_ws/install/setup.bash
~/OUTDOOR_ROBOT/microros/scripts/run_agent.sh
```

Espera logs como `create_publisher`, `create_subscription` o `session established`.

**Terminal 2 — comprobar topics:**

```bash
export ROS_DOMAIN_ID=0
source /opt/ros/jazzy/setup.bash
ros2 node list          # → /outdoor_robot_firmware
ros2 topic echo /hw/joint_states
```

Si faltan topics, pulsa **RESET** en el ESP32 con el agent corriendo.

---

## Checklist

| Check | Comando / acción |
|-------|------------------|
| Puerto existe | `ls -l /dev/ttyUSB*` |
| Permisos | `sudo chmod 666 /dev/ttyUSB0` |
| Mismo domain ID | `echo $ROS_DOMAIN_ID` → `0` en todas las terminales |
| Agent instalado | `source ~/uros_ws/install/setup.bash` |
| Nodo visible | `ros2 node list` → `/outdoor_robot_firmware` |
| Tipo de mensaje | `ros2 topic info /hw/joint_states -v` → `Float64MultiArray` |
| Sin monitor serial | Cierra PlatformIO Monitor mientras corre el agent |
| Distro firmware | `board_microros_distro = jazzy` en `platformio.ini` |

---

## Log del agent

Cuando el ESP32 conecta deberías ver:

```
create_publisher ... hw/joint_states
create_subscription ... hw/joint_commands
```

Si solo hay ping/heartbeat pero **no create_publisher**, el ESP32 no terminó el setup. Reflashea y resetea la placa.

---

## Errores comunes

1. **Leer topics en la misma terminal que el agent** — el agent bloquea esa shell; abre otra terminal.
2. **`ROS_DOMAIN_ID` distinto** — el agent ve topics pero `ros2 topic list` no. Usa `export ROS_DOMAIN_ID=0` en todas.
3. **Agent antes de flashear firmware jazzy** — reflash, luego reset con agent corriendo.
4. **Float32 vs Float64** — debe ser `Float64MultiArray` en ambos lados.
5. **Teclado no responde** — `teleop_twist_keyboard` necesita terminal interactiva (TTY). Usa terminal aparte o `run_teleop_keyboard.sh`.

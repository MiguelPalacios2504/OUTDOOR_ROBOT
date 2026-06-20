# Teleoperación del robot real (micro-ROS)

Guía para mover el robot con el ESP32 y ROS 2 en la Raspberry Pi. **Sin Gazebo, sin Nav2, sin ros2_control** — solo lo mínimo para teleop.

---

## Arquitectura

```text
┌─────────────────┐     serial USB      ┌──────────────────┐
│  ESP32          │◄───────────────────►│  micro_ros_agent │
│  outdoor_robot  │                     │  (Pi, terminal 1)│
│  firmware       │                     └────────┬─────────┘
└────────┬────────┘                              │ DDS
         │                                       │
         │ /hw/joint_commands                    │
         │ /hw/joint_states                      │
         ▼                                       ▼
┌────────────────────────────────────────────────────────────┐
│  teleop_joint_commands_node  (Pi)                          │
│  /cmd_vel  ──►  /hw/joint_commands  (Float64MultiArray)    │
└────────────────────────────▲───────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │ teleop_twist_   │
                    │ keyboard (T2)     │
                    └───────────────────┘
```

**Flujo:** teclado → `/cmd_vel` → `teleop_joint_commands_node` → `/hw/joint_commands` → ESP32 → motores.

---

## Requisitos previos

1. **Firmware flasheado** en el ESP32 (una vez, o tras cambios):

   ```bash
   sudo chmod 666 /dev/ttyUSB0
   ~/OUTDOOR_ROBOT/microros/scripts/upload.sh
   ```

2. **Workspaces compilados y sourced** (en cada terminal):

   ```bash
   export ROS_DOMAIN_ID=0
   export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
   source /opt/ros/jazzy/setup.bash
   source ~/uros_ws/install/setup.bash          # micro_ros_agent
   source ~/OUTDOOR_ROBOT/install/setup.bash    # bot_control, bot_bringup
   ```

3. ESP32 conectado por USB (normalmente `/dev/ttyUSB0`).

---

## Arranque recomendado (3 terminales)

### Terminal 1 — micro-ROS agent

Deja esta terminal **abierta y corriendo**:

```bash
~/OUTDOOR_ROBOT/microros/scripts/run_agent.sh
```

Espera ver `create_publisher` / `create_subscription`. Si no aparecen, pulsa **RESET** en el ESP32.

### Terminal 2 — teleop teclado

**Debe ser una terminal interactiva** (con TTY). Si usas SSH: `ssh -t usuario@pi`.

```bash
~/OUTDOOR_ROBOT/microros/scripts/run_teleop_keyboard.sh
```

Este script arranca el puente `/cmd_vel` → `/hw/joint_commands` y el teclado.

### Terminal 3 (opcional) — monitorizar

```bash
ros2 node list
ros2 topic echo /hw/joint_states
ros2 topic echo /cmd_vel
```

---

## Controles del teclado

| Tecla | Acción |
|-------|--------|
| `i` | Adelante |
| `,` | Atrás |
| `j` | Girar izquierda |
| `l` | Girar derecha |
| `k` o `Space` | Parar |
| `q` / `z` | Subir / bajar velocidad |

---

## Alternativa: launch ROS 2

Arranca agent + puente (sin teclado — el teclado va en terminal aparte):

```bash
ros2 launch bot_bringup teleop_real.launch.py
```

En **otra terminal interactiva**:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Joystick en lugar de teclado:

```bash
ros2 launch bot_bringup teleop_real.launch.py teleop:=joy run_agent:=false
```

(Si el agent ya corre en terminal 1, usa `run_agent:=false`.)

---

## Verificar que todo está bien

```bash
ros2 node list
```

Deberías ver al menos:

- `/outdoor_robot_firmware`
- `/teleop_joint_commands_node`
- `/teleop_twist_keyboard` (cuando teleopéas)

Prueba manual sin teclado:

```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.2}, angular: {z: 0.0}}" -r 10
```

---

## Layout de `/hw/joint_commands`

Array de 8 `float64` (rad/s en ruedas):

| Índice | Significado | Motor ESP32 |
|--------|-------------|-------------|
| 0–3 | Steering (rad) | Ignorado por ahora |
| 4 | Vel. rueda delantera izq. | Motor 1 |
| 5 | Vel. rueda delantera der. | Motor 2 |
| 6 | Vel. rueda trasera izq. | Motor 3 |
| 7 | Vel. rueda trasera der. | Motor 4 |

El nodo `teleop_joint_commands_node` usa modo **tanque**: misma velocidad en ruedas izquierdas (4,6) y derechas (5,7).

---

## Problemas frecuentes

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| Solo `/outdoor_robot_firmware`, no se mueve | Falta nodo de teleop | Terminal 2: `run_teleop_keyboard.sh` |
| Teclado no responde | Terminal sin TTY | Terminal interactiva o `ssh -t` |
| No hay topics | Agent no conectado | Reset ESP32 con agent corriendo |
| `ros2 topic list` vacío en otra terminal | `ROS_DOMAIN_ID` distinto | `export ROS_DOMAIN_ID=0` en todas |
| Puerto ocupado | Monitor serial o otro agent | Cierra PlatformIO Monitor / `pkill micro_ros_agent` |

Más detalle: [`microros/TROUBLESHOOTING.md`](microros/TROUBLESHOOTING.md)

---

## Qué viene después (no incluido aquí)

| Componente | Launch | Cuándo |
|------------|--------|--------|
| Simulación Gazebo | `bot_gazebo/simulation.launch.py` | Desarrollo sin hardware |
| ros2_control + swerve | `bot_bringup/real_robot.launch.py` | Control avanzado 4WIS |
| Nav2 + SLAM | `bot_bringup/real_autonomy.launch.py` | Navegación autónoma |

---

## Referencias

- Firmware ESP32: [`microros/outdoor_robot/README.md`](microros/outdoor_robot/README.md)
- Scripts: [`microros/scripts/`](microros/scripts/)
- Launch teleop: [`src/bot_bringup/launch/teleop_real.launch.py`](src/bot_bringup/launch/teleop_real.launch.py)
- Contrato hardware: [`src/bot_hardware_interface/INTERFACE.md`](src/bot_hardware_interface/INTERFACE.md)

# Teleoperación del robot real (micro-ROS)

Guía para mover el robot con el ESP32 y ROS 2 en la Raspberry Pi. **Sin Gazebo, sin Nav2, sin ros2_control** — solo lo mínimo para teleop.

---

## Arquitectura

```text
┌─────────────────┐     serial USB      ┌──────────────────┐
│  ESP32          │◄───────────────────►│  micro_ros_agent │
│  outdoor_robot  │    /dev/ttyUSB0     │  (Pi, terminal 1)│
│  motores 4-7    │                     └────────┬─────────┘
└────────┬────────┘                              │ DDS
         │                                       │
         │ /hw/joint_commands [4-7]              │
         │ /hw/joint_states                      │
         ▼                                       ▼
┌────────────────────────────────────────────────────────────┐
│  teleop_joint_commands_node  (Pi, terminal 3)              │
│  /cmd_vel  ──►  /hw/joint_commands  (Float64MultiArray)    │
└────────────────────────────▲───────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │ teleop_twist_   │
                    │ keyboard        │
                    └─────────────────┘

┌─────────────────┐     serial USB      ┌──────────────────┐
│  4× servos STS  │◄───────────────────►│  steer_servo_node│
│  dirección      │    /dev/ttyACM0     │  (Pi, terminal 2)│
└─────────────────┘                     └────────▲─────────┘
                                                 │
                              /hw/joint_commands [0-3]
```

**Flujo:** teclado → `/cmd_vel` → `teleop_joint_commands_node` → `/hw/joint_commands` → servos (0–3, Pi) + motores (4–7, ESP32).

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
4. Placa de servos Feetech en la Pi por USB (normalmente `/dev/ttyACM0`).

---

## Arranque automático (Pi)

Instalación única:

```bash
sudo ~/OUTDOOR_ROBOT/microros/scripts/install_pi_setup.sh
```

| Qué | Cómo |
|-----|------|
| SSH en cualquier WiFi | `ssh computer@outdoor-robot.local` |
| SSH por cable ethernet | `ssh computer@192.168.3.20` |
| Agent + servos al boot | systemd `outdoor-robot-agent` + `outdoor-robot-steer` |
| Teleop (solo esto manual) | `run_teleop_keyboard.sh` tras conectar por SSH |

Estado de servicios: `systemctl status outdoor-robot-agent outdoor-robot-steer`

---

## Arranque recomendado (3 terminales)

Los **tres** scripts deben estar corriendo. Sin `run_steer_servos.sh` los motores pueden moverse pero **la dirección no**.

### Terminal 1 — micro-ROS agent (motores ESP32)

Deja esta terminal **abierta y corriendo**:

```bash
~/OUTDOOR_ROBOT/microros/scripts/run_agent.sh
```

Espera ver `create_publisher` / `create_subscription`. Si no aparecen, pulsa **RESET** en el ESP32.

### Terminal 2 — servos de dirección (Pi)

```bash
source ~/OUTDOOR_ROBOT/install/setup.bash
~/OUTDOOR_ROBOT/microros/scripts/run_steer_servos.sh
```

Espera ver `IDs detectados en /dev/ttyACM0` y `Escuchando /hw/joint_commands`.

### Terminal 3 — teleop teclado

**Debe ser una terminal interactiva** (con TTY). Si usas SSH: `ssh -t usuario@pi`.

```bash
~/OUTDOOR_ROBOT/microros/scripts/run_teleop_keyboard.sh
```

Este script arranca el puente `/cmd_vel` → `/hw/joint_commands` y el teclado. **No** sustituye a `run_steer_servos.sh`.

### Terminal 4 (opcional) — monitorizar

```bash
ros2 node list
ros2 topic echo /hw/joint_states
ros2 topic echo /hw/steer_states
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
- `/steer_servo_node`
- `/teleop_joint_commands_node`
- `/teleop_twist_keyboard` (cuando teleopéas)

Prueba manual sin teclado:

```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.2}, angular: {z: 0.0}}" -r 10
```

---

## Layout de `/hw/joint_commands`

Array de 8 `float64`:

| Índice | Significado | Hardware |
|--------|-------------|----------|
| 0 | `f_left_steer` (rad) | Servo id=11 (Pi) |
| 1 | `f_right_steer` (rad) | Servo id=14 (Pi) |
| 2 | `b_leftsteer` (rad) | Servo id=12 (Pi) |
| 3 | `b_rightsteer` (rad) | Servo id=13 (Pi) |
| 4 | Vel. rueda delantera izq. (rad/s) | Motor 1 (ESP32) |
| 5 | Vel. rueda delantera der. (rad/s) | Motor 2 (ESP32) |
| 6 | Vel. rueda trasera izq. (rad/s) | Motor 3 (ESP32) |
| 7 | Vel. rueda trasera der. (rad/s) | Motor 4 (ESP32) |

Configuración de servos: [`src/bot_control/config/steer_servo.yaml`](src/bot_control/config/steer_servo.yaml). Calibración: `run_steer_calibrate.sh`.

---

## Problemas frecuentes

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| Motores sí, dirección no | Falta `run_steer_servos.sh` | Terminal 2: `run_steer_servos.sh` |
| Solo `/outdoor_robot_firmware`, no se mueve | Falta nodo de teleop | Terminal 3: `run_teleop_keyboard.sh` |
| Servo no responde / puerto ocupado | Calibración o doble nodo steer | Cierra `run_steer_calibrate.sh` u otro `steer_servo_node` |
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

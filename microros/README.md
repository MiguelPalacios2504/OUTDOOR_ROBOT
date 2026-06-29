# micro-ROS (ESP32 firmware)

Firmware y scripts para conectar el ESP32 del robot con ROS 2 Jazzy vía **micro-ROS serial**.

## Estructura

```text
microros/
├── outdoor_robot/          # Proyecto PlatformIO (firmware ESP32)
│   ├── src/main.cpp
│   ├── src/motor_controller.cpp
│   ├── include/motor_controller.hpp
│   └── platformio.ini
├── scripts/
│   ├── upload.sh           # Compilar y flashear
│   ├── run_agent.sh        # micro-ROS agent (terminal 1)
│   ├── run_steer_servos.sh # Servos dirección Pi (terminal 2)
│   ├── run_steer_calibrate.sh  # Calibración manual servos
│   └── run_teleop_keyboard.sh  # Teleop teclado (terminal 3)
├── TROUBLESHOOTING.md
└── README.md               # este archivo
```

El firmware antiguo estaba en `~/outdoor_robot` (carpeta suelta). **La copia canónica es ahora `OUTDOOR_ROBOT/microros/outdoor_robot`.**

## Flashear ESP32

```bash
sudo chmod 666 /dev/ttyUSB0
~/OUTDOOR_ROBOT/microros/scripts/upload.sh
```

## Conectar con ROS 2

Ver guía completa de teleoperación: [`../TELEOP.md`](../TELEOP.md)

### Arranque automático en la Pi (recomendado)

Una sola vez en la Raspberry:

```bash
sudo ~/OUTDOOR_ROBOT/microros/scripts/install_pi_setup.sh
```

Eso configura:

- **SSH por nombre** en cualquier WiFi: `ssh computer@outdoor-robot.local`
- **IP fija por cable** (ethernet): `192.168.3.20`
- **Servicios al boot**: `outdoor-robot-agent` (ESP32) + `outdoor-robot-steer` (servos)

Tras encender la Pi + ESP32 + placa servos, solo abres SSH y lanzas el teleop.

### Teleop manual (3 terminales)

| Terminal | Comando |
|----------|---------|
| 1 | `~/OUTDOOR_ROBOT/microros/scripts/run_agent.sh` |
| 2 | `~/OUTDOOR_ROBOT/microros/scripts/run_steer_servos.sh` |
| 3 | `~/OUTDOOR_ROBOT/microros/scripts/run_teleop_keyboard.sh` |

Los **tres** scripts deben estar corriendo para teleop completo (motores + dirección). Con `install_pi_setup.sh`, los terminales 1 y 2 arrancan solos al boot.

No ejecutes `run_steer_calibrate.sh` a la vez (mismo puerto `/dev/ttyACM0`).

## Topics del firmware

| Topic | Tipo | Dirección |
|-------|------|-----------|
| `/hw/joint_commands` | `Float64MultiArray` | Pi → ESP32 |
| `/hw/joint_states` | `Float64MultiArray` | ESP32 → Pi |

Detalle del layout de 8 valores: [`outdoor_robot/README.md`](outdoor_robot/README.md)

## Dependencias en la Pi

- ROS 2 Jazzy: `/opt/ros/jazzy`
- `micro_ros_agent`: workspace `~/uros_ws` (compilado con colcon)
- PlatformIO para flashear: `~/.platformio/penv/bin/pio`

```bash
source /opt/ros/jazzy/setup.bash
source ~/uros_ws/install/setup.bash
source ~/OUTDOOR_ROBOT/install/setup.bash
```

## Problemas

[`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)

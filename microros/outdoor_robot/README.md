# Firmware ESP32 (micro-ROS)

Firmware PlatformIO para el ESP32 del robot outdoor. Publica `/hw/joint_states` y escucha `/hw/joint_commands` vía micro-ROS serial.

Contrato compatible con `bot_hardware_interface` y `teleop_joint_commands_node` en el workspace ROS 2.

## Requisitos

- PlatformIO (`~/.platformio/penv/bin/pio`)
- ESP32 conectado en `/dev/ttyUSB0` (ajustable en `platformio.ini`)
- ROS 2 **Jazzy** (`board_microros_distro = jazzy`)

## Flashear

```bash
sudo chmod 666 /dev/ttyUSB0
cd ~/OUTDOOR_ROBOT/microros/outdoor_robot
pio run -e esp32dev -t upload
```

O desde scripts:

```bash
~/OUTDOOR_ROBOT/microros/scripts/upload.sh
```

Si cambiaste la distro ROS, limpia micro-ROS antes:

```bash
pio run --target clean_microros
pio run -e esp32dev -t upload
```

**No abras el monitor serial de PlatformIO mientras corre el agent.**

## Topics

| Topic | Tipo | Dirección | Rate |
|-------|------|-----------|------|
| `/hw/joint_commands` | `std_msgs/Float64MultiArray` | ROS 2 → ESP32 | ~100 Hz |
| `/hw/joint_states` | `std_msgs/Float64MultiArray` | ESP32 → ROS 2 | 100 Hz |

Nodo firmware: `/outdoor_robot_firmware`

### Layout del array (8 valores)

| Índice | Joint | Unidad | ESP32 |
|--------|-------|--------|-------|
| 0–3 | steering | rad | ignorado (sin servos aún) |
| 4 | `f_leftwheel` | rad/s | motor 1 |
| 5 | `f_rightwheel` | rad/s | motor 2 |
| 6 | `b_leftwheel` | rad/s | motor 3 |
| 7 | `b_rightwheel` | rad/s | motor 4 |

## Prueba manual (sin teleop)

Con el agent corriendo:

```bash
ros2 topic pub -r 10 /hw/joint_commands std_msgs/msg/Float64MultiArray \
  "{data: [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0]}"

ros2 topic echo /hw/joint_states
```

Ver también: [`../TROUBLESHOOTING.md`](../TROUBLESHOOTING.md)

# OUTDOOR_ROBOT — ROS 2 workspace

Workspace de [ROS 2 Jazzy](https://docs.ros.org/) para un robot móvil outdoor con **4 ruedas independientes (4WIS/4WID / swerve)**. El código fuente vive bajo `src/`; tras compilar con `colcon`, los artefactos aparecen en `build/`, `install/` y `log/` (no commitear como código fuente).

Rama activa para el robot físico en Raspberry Pi: **`pi`**.

---

## Estructura del workspace

| Carpeta | Contenido |
|---------|-----------|
| `src/` | Paquetes ROS 2 (código fuente) |
| `microros/` | Firmware ESP32 + scripts de teleop real |
| `maps/` | Mapas para localización (`arena_map`, `terrain_cost`) |
| `scripts/` | Instalación de dependencias, utilidades |
| `basic_scripts/`, `tools/`, `debug_logs/` | Scripts auxiliares y logs |
| `build/`, `install/`, `log/` | Salida de `colcon build` |

---

## Paquetes ROS 2 (`src/`)

```text
src/
├── bot_description/        # URDF/Xacro, mallas, RViz
├── bot_control/            # Cinemática swerve, ros2_control, nodos de control
├── bot_gazebo/             # Simulación en Gazebo Sim
├── bot_bringup/            # Robot real: teleop, bringup, autonomía
├── bot_localization/       # EKF, laser odom, SLAM, AMCL
├── bot_planning/           # Nav2 (planificación y control)
├── bot_sensors/            # Sensores del robot real
├── bot_hardware_interface/ # Interfaz hardware ROS 2
├── bot_debug/              # Logging CSV y plots offline
├── csm/                    # Scan matching (vendored)
└── ros2_laser_scan_matcher/ # Laser odometry (vendored)
```

Dependencias externas (vía `bot_sources.repos`):

- `robot_localization` — filtro EKF (paquete ROS)
- `microros/outdoor_robot` — firmware ESP32 (PlatformIO + micro-ROS serial)

---

## Firmware ESP32 (`microros/outdoor_robot/`)

- **PlatformIO**, board ESP32, micro-ROS por serial con **ROS 2 Jazzy**
- Controla **4 motores** con encoders (8 joints: steer + drive por rueda)
- Topics: `/hw/joint_commands` y `/hw/joint_states`

Scripts útiles en `microros/scripts/`:

| Script | Terminal | Uso |
|--------|----------|-----|
| `run_agent.sh` | 1 | micro-ROS agent (motores ESP32, `/dev/ttyUSB0`) |
| `run_steer_servos.sh` | 2 | Servos de dirección (Pi, `/dev/ttyACM0`) |
| `run_teleop_keyboard.sh` | 3 | Teleop por teclado (puente `/cmd_vel` → `/hw/joint_commands`) |
| `run_steer_calibrate.sh` | — | Calibración manual de servos (no junto con los anteriores) |
| `upload.sh` | — | Flashear firmware al ESP32 |

Documentación adicional: [`microros/README.md`](microros/README.md), [`microros/TROUBLESHOOTING.md`](microros/TROUBLESHOOTING.md)

---

## Modos de uso

### 1. Teleop real (mínimo — sin Gazebo, sin Nav2)

Guía completa: **[`TELEOP.md`](TELEOP.md)**

```bash
# Terminal 1 — agent (motores ESP32)
~/OUTDOOR_ROBOT/microros/scripts/run_agent.sh

# Terminal 2 — servos de dirección (obligatorio)
~/OUTDOOR_ROBOT/microros/scripts/run_steer_servos.sh

# Terminal 3 — teclado (terminal interactiva)
~/OUTDOOR_ROBOT/microros/scripts/run_teleop_keyboard.sh
```

Flujo: teclado → `/cmd_vel` → `teleop_joint_commands_node` → `/hw/joint_commands` → servos (índices 0–3, Pi) + motores (índices 4–7, ESP32).

Guía detallada: [`TELEOP.md`](TELEOP.md)

### 2. Simulación completa (3 terminales)

Un paquete por terminal (`cd OUTDOOR_ROBOT && source install/setup.bash`):

| # | Paquete | Comando |
|---|---------|---------|
| 1 | `bot_gazebo` | `ros2 launch bot_gazebo simulation.launch.py` |
| 2 | `bot_localization` | `ros2 launch bot_localization localization.launch.py` |
| 3 | `bot_planning` | `ros2 launch bot_planning navigation.launch.py use_sim_time:=true` |

Espera T1 antes de T2; T2 (`/map`, AMCL) antes de T3. En RViz (T2): **2D Goal Pose**.

### 3. Robot real con autonomía

Launches en `bot_bringup`:

| Launch | Uso |
|--------|-----|
| `teleop_real.launch.py` | Solo teleop micro-ROS (agent + puente) |
| `real_robot.launch.py` | URDF + ros2_control + swerve |
| `real_autonomy.launch.py` | Sensores + localización + Nav2 opcional |

---

## Detalle por paquete

### `bot_description`

Modelo físico canónico del bot.

**Contenido:** `urdf/bot_v1.*.xacro`, `meshes/`, `launch/load_urdf.launch.py`, `launch/rviz.launch.py`, `rviz/display.rviz`.

El modelo limpio es `bot_v1.urdf.xacro`; Gazebo y `ros2_control` están en `bot_v1.gazebo.xacro`.

### `bot_control`

Cinemática swerve (`swerve_cmd_node`, `joint_command_bridge`, `teleop_joint_commands_node`) + `ros2_controllers.yaml`.

**Launch:** `control.launch.py`

### `bot_gazebo`

Solo Gazebo Sim — robot, lidar, cámara, `ros2_control`, control swerve. **Sin** SLAM, AMCL ni Nav2.

**Launch principal:** `ros2 launch bot_gazebo simulation.launch.py`

**Stack:** `simulation.launch.py` → `simulate_robot.launch.py` → `spawn_robot.launch.py` + `bot_control`.

### `bot_bringup`

Robot real — bringup, teleop y stacks completos. Ver [Modos de uso](#modos-de-uso) y [`TELEOP.md`](TELEOP.md).

Simulación: `bot_gazebo`. Localización: `bot_localization`. Navegación: `bot_planning`.

### `bot_localization`

Estimación de estado y pose con mapa (EKF, laser odom, SLAM, AMCL). Ejecutar en una **segunda terminal** tras la sim.

**Launch principal:** `ros2 launch bot_localization localization.launch.py`

### `bot_planning`

Planificación y control Nav2. Ejecutar en una **tercera terminal** tras localización.

**Launch principal:** `ros2 launch bot_planning navigation.launch.py use_sim_time:=true`

Contrato de interfaz: `src/bot_planning/INTERFACE.md`

### `bot_sensors`

Drivers y nodos de sensores del robot real (lidar, IMU, etc.).

### `bot_hardware_interface`

Interfaz `ros2_control` para el hardware del robot físico.

### `bot_debug`

Logging CSV y plots offline para depuración.

---

## Build

```bash
cd ~/OUTDOOR_ROBOT
source /opt/ros/jazzy/setup.bash
bash scripts/install_jazzy_sim_deps.sh   # una vez: ros2_control + gz_ros2_control
colcon build --symlink-install
source install/setup.bash
```

Tras renombrar paquetes, usa una **terminal nueva** o ejecuta `colcon build` en un shell que **no** haya hecho source de un `install/setup.bash` antiguo (entradas obsoletas de `AMENT_PREFIX_PATH` causan errores de launch). Si persisten problemas:

```bash
rm -rf build install log
colcon build --symlink-install
source install/setup.bash
```

---

## Maps

Mapas guardados para localización en `maps/` (p. ej. `maps/arena_map.yaml`, `maps/terrain_cost.yaml`).

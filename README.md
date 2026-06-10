# OUTDOOR_ROBOT — ROS 2 workspace

This repository is a [ROS 2](https://docs.ros.org/) workspace for the outdoor mobile **bot** platform (four-wheel independent steer/drive, 4WIS/4WID). Packages live under `src/`. After building with `colcon`, outputs appear under `build/`, `install/`, and `log/` (do not commit those as source code).

---

## Package layout

```text
src/
├── bot_description/   # URDF/Xacro, meshes, RViz, load_urdf.launch.py
├── bot_control/       # Swerve kinematics, ros2_control config, spawners
├── bot_gazebo/        # Gazebo Sim, gz_bridge, simulation launch stack
├── bot_bringup/       # Real robot only — bringup.launch.py
├── bot_localization/  # EKF, laser odom, SLAM, AMCL
├── bot_planning/      # Nav2 planner, controller, behaviors
└── bot_debug/         # CSV logging and plotting tools
```

External dependencies (vendored or via `bot_sources.repos`):

- `csm` — scan matching
- `ros2_laser_scan_matcher` — laser odometry
- `robot_localization` — EKF filter (ROS package)

---

## `bot_description`

**Role:** Canonical physical model of the bot.

**Contents:** `urdf/bot_v1.*.xacro`, `meshes/`, `launch/load_urdf.launch.py`, `launch/rviz.launch.py`, `rviz/display.rviz`.

The clean model is `bot_v1.urdf.xacro`; Gazebo and `ros2_control` are in `bot_v1.gazebo.xacro`.

---

## `bot_control`

**Role:** Swerve (`swerve_cmd_node`, `joint_command_bridge`) + `ros2_controllers.yaml`.

**Launch:** `control.launch.py` (un solo launch en este paquete).

---

## `bot_gazebo`

**Role:** Gazebo Sim only — robot, lidar, camera, `ros2_control`, swerve control. **No** SLAM, AMCL, or Nav2.

**Main launch:** `ros2 launch bot_gazebo simulation.launch.py`

**Launch stack:** `simulation.launch.py` → `simulate_robot.launch.py` → `spawn_robot.launch.py` + `bot_control`.

---

## `bot_bringup`

**Role:** **Solo robot real** — `bringup.launch.py` (URDF + `control.launch.py`, `use_sim_time:=false`).

Simulación: `bot_gazebo`. Localización: `bot_localization`. Navegación: `bot_planning`.

---

## `bot_localization`

**Role:** State estimation and map-based pose (EKF, laser odom, SLAM, AMCL). Run in a **second terminal** after sim.

**Main launch:** `ros2 launch bot_localization localization.launch.py`

---

## `bot_planning`

**Role:** Nav2 planning and control. Run in a **third terminal** after localization.

**Main launch:** `ros2 launch bot_planning navigation.launch.py use_sim_time:=true`

Contract: `src/bot_planning/INTERFACE.md`

---

## `bot_debug`

**Role:** Debug CSV logging and offline plots.

---

## Build

```bash
cd /path/to/OUTDOOR_ROBOT
source /opt/ros/jazzy/setup.bash
bash scripts/install_jazzy_sim_deps.sh   # once: ros2_control + gz_ros2_control
colcon build --symlink-install
source install/setup.bash
```

After renaming packages, use a **new terminal** or run `colcon build` in a shell that has **not** sourced an old `install/setup.bash` (stale `AMENT_PREFIX_PATH` entries for `robby_*`, `robot_*`, or `bot_estimation` cause launch errors). If problems persist:

```bash
rm -rf build install log
colcon build --symlink-install
source install/setup.bash
```

### Simulación + localización + navegación

Un paquete por terminal (`cd OUTDOOR_ROBOT && source install/setup.bash`):

| # | Paquete | Comando |
|---|---------|---------|
| 1 | `bot_gazebo` | `ros2 launch bot_gazebo simulation.launch.py` |
| 2 | `bot_localization` | `ros2 launch bot_localization localization.launch.py` (mapa + AMCL + RViz) |
| 3 | `bot_planning` | `ros2 launch bot_planning navigation.launch.py use_sim_time:=true` |

Espera T1 antes de T2; T2 (`/map`, AMCL) antes de T3. En RViz (T2): **2D Goal Pose**.

---

## Maps

Saved maps for localization live under `maps/` at the workspace root (e.g. `maps/arena_map.yaml`).



nuevo 
lanzar real 


ros2 launch bot_bringup real_autonomy.launch.py 


### Teleop por teclado (solo comunicación, sin navegación)

En la Raspberry Pi, con el ESP32 conectado por USB:

```bash
# Terminal 1 — agente micro-ROS
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 -b 115200

# Terminal 2 — teclado + puente /cmd_vel -> /hw/joint_commands
source install/setup.bash
ros2 launch bot_control teleop.launch.py
```

Flujo: `teleop_twist_keyboard` publica `/cmd_vel` → `teleop_joint_commands_node` convierte a cinemática swerve → publica `/hw/joint_commands` (8 valores: 4 direcciones + 4 velocidades de rueda). El firmware responde en `/hw/joint_states`.

Solo el puente (sin lanzar el teclado automáticamente):

```bash
ros2 launch bot_control teleop.launch.py run_keyboard:=false
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```



lanzar microros 

conda deactivate
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
source /opt/ros/jazzy/setup.bash
ros2 daemon stop
ros2 daemon start
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 -b 115200 -v6




para ver los topicos 

conda deactivate
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
source /opt/ros/jazzy/setup.bash

ros2 node list
ros2 topic list
ros2 topic echo /hw/joint_states

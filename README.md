# OUTDOOR_ROBOT — ROS 2 workspace

This repository is a [ROS 2](https://docs.ros.org/) workspace for the outdoor mobile **bot** platform (four-wheel independent steer/drive, 4WIS/4WID). Packages live under `src/`. After building with `colcon`, outputs appear under `build/`, `install/`, and `log/` (do not commit those as source code).

---

## Package layout

```text
src/
├── bot_description/   # URDF/Xacro, meshes, RViz
├── bot_control/       # Swerve kinematics, cmd + joint bridge
├── bot_gazebo/        # Gazebo Sim, ros2_control, simulation launch
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

**Contents:** `urdf/bot_v1.*.xacro`, `meshes/`, `launch/display.launch.py`, `rviz/display.rviz`.

The clean model is `bot_v1.urdf.xacro`; Gazebo and `ros2_control` are in `bot_v1.gazebo.xacro`.

---

## `bot_control`

**Role:** Swerve drive command generation and joint-level bridging to `ros2_control`.

**Nodes:** `swerve_cmd_node`, `joint_command_bridge`.

---

## `bot_gazebo`

**Role:** Gazebo Sim only — robot, lidar, camera, `ros2_control`, swerve control. **No** SLAM, AMCL, or Nav2.

**Main launch:** `ros2 launch bot_gazebo sim_swerve.launch.py`

See `src/bot_gazebo/README.md` for the multi-terminal workflow.

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
source /opt/ros/<DISTRO>/setup.bash   # e.g. jazzy or humble
colcon build --symlink-install
source install/setup.bash
```

After renaming packages, use a **new terminal** or run `colcon build` in a shell that has **not** sourced an old `install/setup.bash` (stale `AMENT_PREFIX_PATH` entries for `robby_*`, `robot_*`, or `bot_estimation` cause launch errors). If problems persist:

```bash
rm -rf build install log
colcon build --symlink-install
source install/setup.bash
```

### Operación en 4 terminales (reemplaza el launch único antiguo)

**Antes (todo en uno):**

```bash
ros2 launch bot_gazebo sim_swerve.launch.py \
  enable_slam:=false enable_saved_map_localization:=true enable_nav2:=true \
  enable_laser_odometry:=true use_camera:=true
```

**Ahora** — mismo comportamiento, en este orden (cada terminal: `cd OUTDOOR_ROBOT && source install/setup.bash`):

| # | Qué | Comando |
|---|-----|---------|
| 1 | Robot, Gazebo, controladores, lidar, cámara | `ros2 launch bot_gazebo sim_swerve.launch.py use_camera:=true` |
| 2 | Localización (EKF, laser odom, AMCL en mapa) | `ros2 launch bot_localization localization.launch.py enable_slam:=false enable_saved_map_localization:=true enable_laser_odometry:=true map_yaml_file:=$(pwd)/maps/arena_map.yaml` |
| 3 | Navegación (Nav2) | `ros2 launch bot_planning navigation.launch.py use_sim_time:=true` |
| 4 | RViz | `ros2 launch bot_localization localization_rviz.launch.py` |

Espera a que el terminal 1 muestre Gazebo y controladores activos antes de lanzar el 2; espera mapa + AMCL antes del 3.

---

## Maps

Saved maps for localization live under `maps/` at the workspace root (e.g. `maps/arena_map.yaml`).

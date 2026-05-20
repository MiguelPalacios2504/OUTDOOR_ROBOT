# OUTDOOR_ROBOT — ROS 2 workspace

This repository is a [ROS 2](https://docs.ros.org/) workspace for the outdoor mobile **bot** platform (four-wheel independent steer/drive, 4WIS/4WID). Packages live under `src/`. After building with `colcon`, outputs appear under `build/`, `install/`, and `log/` (do not commit those as source code).

---

## Package layout

```text
src/
├── bot_description/   # URDF/Xacro, meshes, RViz
├── bot_control/       # Swerve kinematics, cmd + joint bridge
├── bot_gazebo/        # Gazebo Sim, ros2_control, simulation launch
├── bot_localization/    # EKF, laser odom, SLAM, Nav2 hooks
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

**Role:** Simulation bring-up (Gazebo Sim, bridges, controller spawners).

**Main launch:** `ros2 launch bot_gazebo sim_swerve.launch.py`

**Helper script:** `ros2 run bot_gazebo sim_with_logging`

---

## `bot_localization`

**Role:** Sensor fusion and mapping stack (wheel + IMU EKF, optional laser odometry, SLAM, AMCL, Nav2).

**Main launch:** included from `sim_swerve.launch.py` when `enable_localization:=true`.

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

### Simulation example

```bash
source install/setup.bash
ros2 launch bot_gazebo sim_swerve.launch.py
```

---

## Maps

Saved maps for localization live under `maps/` at the workspace root (e.g. `maps/arena_map.yaml`).

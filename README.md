# OUTDOOR_ROBOT — `3d_development` branch

ROS 2 workspace for **3D simulation** of the outdoor **bot** platform (4WIS/4WID). This branch keeps only the sim stack; localization and planning live on `development`.

---

## Packages (`src/`)

```text
src/
├── bot_description/     # URDF/Xacro, meshes, RViz
├── bot_control/         # Swerve kinematics, cmd + joint bridge
├── bot_gazebo/          # Gazebo Sim, ros2_control, simulation launch
├── bot_teleoperation/   # Keyboard teleop (/cmd_vel)
├── bot_mapping/         # LIO-SAM 3D mapping (lidar + IMU)
└── bot_debug/           # CSV logging and plotting tools
```

---

## Build

```bash
cd /path/to/OUTDOOR_ROBOT
source /opt/ros/<DISTRO>/setup.bash
colcon build --symlink-install
source install/setup.bash
```

On `3d_development`, use a **fresh** overlay after switching branches (stale `install/bot_planning` breaks Gazebo launch):

```bash
rm -rf build install log
colcon build --symlink-install
source install/setup.bash   # new terminal or re-source after clean
```

---

## Simulation

```bash
ros2 launch bot_gazebo sim_swerve.launch.py
```

**Teleop** (second terminal, Gazebo playing):

```bash
ros2 launch bot_teleoperation teleop.launch.py use_sim_time:=true
```

Focus the teleop terminal. Holonomic: `w/a/s/d` + diagonals, `q/e` or `z/c` for yaw, arrows OK, `x` stop. See `bot_teleoperation/README.md`.

Optional: `use_lidar:=true`, `use_camera:=true`, `use_gnss:=true` (defaults in `bot_gazebo/config/sim_swerve.yaml`).

**GNSS** (`sensor_msgs/NavSatFix` on `/gnss/fix`, frame `gnss_link`). World origin WGS84 in `bot_description/config/bot_gnss.yaml` (must match `bot_gazebo/worlds/*.world.sdf`):

```bash
ros2 topic echo /gnss/fix --once -s
ros2 topic hz /gnss/fix -s
```

3D LiDAR: **Unitree 4D-LiDAR L2** per datasheet in `bot_description/config/unitree_4d_lidar_l2.yaml` — Gazebo base topic `/lidar` (Harmonic appends `/points` for `PointCloudPacked`, same as [MOGI-ROS Week-5-6](https://github.com/MOGI-ROS/Week-5-6-Gazebo-sensors) `scan` + `scan/points`). ROS: `/lidar` (`LaserScan`), `/lidar/points` (`PointCloud2`), frame `lidar_link`.

**Check lidar (second terminal, sim must be running):**

```bash
source install/setup.bash
# Sim running, Gazebo Play (not paused), ~40 s after spawn

# Gazebo transport (note: -l list, -f frequency; NOT "gz topic list")
gz topic -l | grep lidar
gz topic -i -t /lidar/points    # expect PointCloudPacked
gz topic -f -t /lidar/points

# ROS (bridged by sim_bridge in ros_gz_bridge.yaml)
ros2 node list | grep sim_bridge
ros2 topic list | grep lidar
ros2 topic hz /lidar/points -s
ros2 topic echo /lidar/points --once -s --qos-reliability best_effort
```

If `/lidar/points` is missing: clean rebuild (`rm -rf build install log && colcon build`). If the topic exists but no data: unpause Gazebo, wait longer, or use `use_camera:=false` for GPU headroom.

Visualize the model without Gazebo:

```bash
ros2 launch bot_description display.launch.py
```

Debug logging:

```bash
ros2 launch bot_debug debug_tools.launch.py
```

---

## Other branches

- **`development`** — full stack: `bot_localization`, `bot_planning`, maps, Nav2.

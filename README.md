# OUTDOOR_ROBOT — `3d_development` branch

ROS 2 workspace for **3D simulation** of the outdoor **bot** platform (4WIS/4WID). This branch keeps only the sim stack; localization and planning live on `development`.

---

## Packages (`src/`)

```text
src/
├── bot_description/   # URDF/Xacro, meshes, RViz
├── bot_control/       # Swerve kinematics, cmd + joint bridge
├── bot_gazebo/        # Gazebo Sim, ros2_control, simulation launch
└── bot_debug/         # CSV logging and plotting tools
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

Optional: `use_lidar:=true`, `use_camera:=true` (defaults in `bot_gazebo/config/sim_swerve.yaml`).

3D LiDAR: **Unitree 4D-LiDAR L2** per datasheet in `bot_description/config/unitree_4d_lidar_l2.yaml` — topic `/lidar/points`, frame `lidar_link`, 360°×96° FOV, 0.05–30 m, 128k pts/s @ 5.55 Hz.

**Check lidar (second terminal, sim must be running):**

```bash
source install/setup.bash
# Wait until Gazebo is playing (not paused) and ~30 s after spawn
ros2 topic list | grep lidar
ros2 topic info /lidar/points -v          # expect Publisher count >= 1
ros2 topic echo /lidar/points --once --qos-reliability best_effort
ros2 topic hz /lidar/points --qos-reliability best_effort
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

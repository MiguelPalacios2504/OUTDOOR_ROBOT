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

---

## Simulation

```bash
ros2 launch bot_gazebo sim_swerve.launch.py
```

Optional: `use_lidar:=true`, `use_camera:=true` (defaults in `bot_gazebo/config/sim_swerve.yaml`).

3D LiDAR (Unitree 4D-LiDAR L2 model in sim): topic `/lidar/points` (`sensor_msgs/PointCloud2`), frame `lidar_link`.

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

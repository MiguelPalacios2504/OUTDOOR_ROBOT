# OUTDOOR_ROBOT — `3d_development` branch

ROS 2 workspace for **3D simulation** of the outdoor **bot** platform (4WIS/4WID): FAST-LIO2 mapping, saved PCD maps, and scan-to-map relocalization. Nav2 / 2D planning lives on `development`.

---

## Packages (`src/`)

```text
src/
├── bot_description/     # URDF/Xacro, meshes, RViz
├── bot_control/         # Swerve kinematics, cmd + joint bridge
├── bot_gazebo/          # Gazebo Sim, ros2_control, simulation launch
├── bot_teleoperation/   # Keyboard teleop (/cmd_vel)
├── bot_mapping/         # FAST-LIO2 mapping + 3D localization
└── bot_debug/           # CSV logging and plotting tools
```

---

## Build (once per machine)

```bash
cd ~/Documents/GITHUB/OUTDOOR_ROBOT
source /opt/ros/jazzy/setup.bash

# After switching branches, use a clean overlay:
rm -rf build install log

colcon build --symlink-install
source install/setup.bash
```

**Localization Python dependency (ICP):**

```bash
pip3 install --break-system-packages open3d
```

In every new terminal:

```bash
source ~/Documents/GITHUB/OUTDOOR_ROBOT/install/setup.bash
```

---

## Part 1 — Create a 3D map (FAST-LIO2)

Use **four terminals**. Press **Play** in Gazebo and wait ~40 s for lidar data.

**Terminal 1 — Gazebo**

```bash
ros2 launch bot_gazebo sim_swerve.launch.py
```

**Terminal 2 — RViz** (`sim_lidar.rviz`: lidar, live `/Laser_map`, robot)

```bash
ros2 launch bot_gazebo sim_rviz.launch.py
```

In RViz: **Fixed Frame** → `camera_init`, enable **PointCloud2** → `/Laser_map` if needed.

**Terminal 3 — Teleop**

```bash
ros2 launch bot_teleoperation teleop.launch.py use_sim_time:=true
```

Drive slowly with `w/a/s/d`, yaw `q/e`, stop `x`. Cover the full area.

**Terminal 4 — FAST-LIO mapping**

```bash
ros2 launch bot_mapping fast_lio.launch.py use_sim_time:=true
```

If FAST-LIO crashes or logs `No Effective Points`:

```bash
ros2 launch bot_mapping fast_lio.launch.py use_sim_time:=true \
  use_lidar_adapter:=false config_file:=fast_lio_unitree_l2_sim.yaml
```

**Save the map**

```bash
ros2 service call /map_save std_srvs/srv/Trigger
cp /tmp/fast_lio_map.pcd ~/Documents/GITHUB/OUTDOOR_ROBOT/maps/my_map.pcd
```

Verify (optional):

```bash
pcl_viewer ~/Documents/GITHUB/OUTDOOR_ROBOT/maps/my_map.pcd
ros2 topic hz /Laser_map -s
```

---

## Part 2 — 3D localization (saved PCD)

Load a map **as-is** (no offline preprocessing). Default map: `maps/mi_mapa_sim.pcd`.

Use **four terminals**. Keep the robot **still** until logs show `Localization OK`.

**Terminal 1 — Gazebo**

```bash
ros2 launch bot_gazebo sim_swerve.launch.py
```

**Terminal 2 — RViz** (includes **SavedMap** `/map` and **2D Pose Estimate** → `/initialpose`)

```bash
ros2 launch bot_gazebo sim_rviz.launch.py
```

Set **Fixed Frame** → `map` to view the saved map and robot together.

**Terminal 3 — Teleop**

```bash
ros2 launch bot_teleoperation teleop.launch.py use_sim_time:=true
```

**Terminal 4 — Localization** (no RViz window)

```bash
ros2 launch bot_mapping fast_lio_localization.launch.py use_sim_time:=true \
  pcd_map_path:=$(pwd)/maps/mi_mapa_sim.pcd
```

**Initial pose** (required once):

- RViz: tool **2D Pose Estimate** on the map (rough guess where the robot is), or
- Terminal:

```bash
ros2 run bot_mapping publish_initial_pose 0 0 0 0 0 0 --ros-args -p use_sim_time:=true
```

**Check**

```bash
ros2 topic hz /map -s
ros2 topic hz /localization -s
```

| Topic | Frame | Role |
|-------|-------|------|
| `/map` | `map` | Saved PCD (RViz **SavedMap**) |
| `/cloud_registered` | `camera_init` | Live scan |
| `/localization` | `map` → `body` | Fused pose in map |

More detail: `src/bot_mapping/README.md`.

---

## Simulation quick reference

```bash
ros2 launch bot_gazebo sim_swerve.launch.py
ros2 launch bot_teleoperation teleop.launch.py use_sim_time:=true
```

3D LiDAR: `/lidar/points` (`PointCloud2`), frame `lidar_link`. Check after Play:

```bash
ros2 topic hz /lidar/points -s
```

If `/lidar/points` is missing: clean rebuild. If no data: unpause Gazebo, wait ~40 s, or `use_camera:=false`.

---

## Other branches

- **`development`** — 2D stack: `bot_localization`, `bot_planning`, occupancy maps, Nav2.

# bot_mapping

3D mapping with **[FAST-LIO2](https://github.com/hku-mars/FAST_LIO)** (LiDAR–inertial odometry) for the outdoor bot.

**Bringup is separate from sim:** `fast_lio.launch.py` does not start Gazebo or RViz. Run simulation and visualization from `bot_gazebo` (see §3).

Uses sim/robot topics:

| Topic | Message | Frame |
|-------|---------|-------|
| `/lidar/points` | `sensor_msgs/PointCloud2` | `lidar_link` |
| `/fast_lio/points` | `sensor_msgs/PointCloud2` | `lidar_link` (sim, after adapter) |
| `/imu/data` | `sensor_msgs/Imu` | `imu_link` |

Gazebo publishes plain `PointCloud2` on `/lidar/points`. `unitree_lidar_adapter` adds `ring` + `time` for the FAST-LIO Velodyne handler → `/fast_lio/points`.

Config: `config/fast_lio_unitree_l2.yaml` (Unitree L2: **39** scan lines, **5.55 Hz**, extrinsics lidar↔IMU).

---

## 1. Install FAST-LIO (once per machine)

**ROS 2 Jazzy:** use upstream branch `ROS2`. `fast_lio` requires the `livox_ros_driver2` **message package** at compile time (Livox driver not used for Unitree L2). This workspace ships a **messages-only** stub at `src/livox_ros_driver2/`.

```bash
sudo apt install -y \
  ros-jazzy-pcl-conversions \
  ros-jazzy-pcl-msgs \
  ros-jazzy-tf2-ros \
  libpcl-dev

# Not in Jazzy apt: ros-jazzy-pcl-ros, ros-jazzy-perception-pcl (removed from FAST_LIO patch)

cd ~/Documents/GITHUB/OUTDOOR_ROBOT

# FAST_LIO is vendored under src/FAST_LIO/ (Jazzy patch already applied).
# Fresh clone without vendored tree:
#   vcs import src < src/bot_mapping/repos/fast_lio.repos
#   cd src/FAST_LIO && git submodule update --init --recursive && cd ../..
#   patch -p1 -d src/FAST_LIO < src/bot_mapping/patches/fast_lio_jazzy.patch

# Patch: C++17, drop pcl_ros, IMU SensorDataQoS (Jazzy)
colcon build --packages-select livox_ros_driver2 fast_lio bot_mapping --symlink-install
source install/setup.bash
```

---

## 2. Build `bot_mapping`

```bash
cd ~/Documents/GITHUB/OUTDOOR_ROBOT
colcon build --packages-select bot_mapping --symlink-install
source install/setup.bash
```

---

## 3. Run mapping in simulation (four terminals)

Start **Gazebo**, **RViz**, **teleop**, and **mapping** independently.

**Terminal 1 — Gazebo:**

```bash
source install/setup.bash
ros2 launch bot_gazebo sim_swerve.launch.py
```

Press **Play** in Gazebo.

**Terminal 2 — RViz** (`sim_lidar.rviz`):

```bash
source install/setup.bash
ros2 launch bot_gazebo sim_rviz.launch.py
```

**Terminal 3 — teleop:**

```bash
source install/setup.bash
ros2 launch bot_teleoperation teleop.launch.py use_sim_time:=true
```

**Terminal 4 — FAST-LIO2 only** (after sim is running):

```bash
source install/setup.bash
ros2 launch bot_mapping fast_lio.launch.py use_sim_time:=true
```

If `fastlio_mapping` crashes (exit -11) or logs `No Effective Points`, try **without the velodyne adapter**:

```bash
ros2 launch bot_mapping fast_lio.launch.py use_sim_time:=true \
  use_lidar_adapter:=false config_file:=fast_lio_unitree_l2_sim.yaml
```

To see the map in your RViz session, add **PointCloud2** → `/Laser_map`, **Fixed Frame** `camera_init`.

**Optional — mapping’s own RViz** (`mapping_fast_lio.rviz`):

```bash
ros2 launch bot_mapping fast_lio.launch.py use_sim_time:=true use_rviz:=true
```

**Real robot** (driver on `/lidar/points`, no adapter):

```bash
ros2 launch bot_mapping fast_lio.launch.py \
  use_lidar_adapter:=false \
  config_file:=fast_lio_unitree_l2_direct.yaml
```

---

## 4. Useful topics

```bash
ros2 topic hz /fast_lio/points -s
ros2 topic hz /Odometry -s
ros2 topic list | grep -E 'cloud|Laser|path|Odometry'
```

RViz **Fixed Frame**: `camera_init`. Map cloud: `/Laser_map`, registered scan: `/cloud_registered`.

Saved PCD (on exit): `/tmp/fast_lio_map.pcd` (see `map_file_path` in yaml).

---

## 5. Tuning

| File | What to change |
|------|----------------|
| `config/fast_lio_unitree_l2.yaml` | `point_filter_num`, extrinsics, `det_range`, `fov_degree` |
| `unitree_lidar_adapter` params | `n_scan`, vertical FOV bins |
| `bot_description/config/unitree_4d_lidar_l2.yaml` | sim lidar grid / rate |

If mapping is slow, increase `point_filter_num` (e.g. 8–10) or reduce `horizontal_samples` / `vertical_samples` in the lidar yaml.

---

## 6. 3D localization (saved PCD, no offline preprocessing)

Relocalize in a pre-built map using the [FAST-LIO localization](https://github.com/HViktorTsoi/FAST_LIO_LOCALIZATION) pattern: FAST-LIO provides high-rate odometry; `global_localization` runs scan-to-map ICP against the saved `.pcd` (loaded as-is).

**Python dep (once, for ICP):**

```bash
pip3 install --break-system-packages open3d
```

See root `README.md` **Part 2** for the full four-terminal localization workflow.

Launch only (RViz via `bot_gazebo sim_rviz.launch.py`):

```bash
ros2 launch bot_mapping fast_lio_localization.launch.py use_sim_time:=true \
  pcd_map_path:=$(pwd)/maps/mi_mapa_sim.pcd
```

Initial pose: RViz **2D Pose Estimate** or `publish_initial_pose`. Keep the robot still until `Localization OK`.

| Topic | Frame | Role |
|-------|-------|------|
| `/map` | `map` | Saved PCD for RViz **SavedMap** |
| `/cloud_registered` | `camera_init` | Live scan (FAST-LIO) |
| `/map_to_odom` | `map` | ICP correction |
| `/localization` | `map` → `body` | Fused pose in map |

RViz **Fixed Frame**: `map`. Use `bot_gazebo` `sim_rviz.launch.py` (not localization’s own RViz).

---

## Architecture

```text
/lidar/points (Gazebo) ──► unitree_lidar_adapter ──► /fast_lio/points
/imu/data ───────────────────────────────────────────► fastlio_mapping
FAST-LIO2 ──► /Odometry, /cloud_registered, /Laser_map, /path
TF: camera_init → body
```

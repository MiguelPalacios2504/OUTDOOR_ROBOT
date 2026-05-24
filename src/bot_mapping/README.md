# bot_mapping

3D mapping with **[LIO-SAM](https://github.com/TixiaoShan/LIO-SAM)** (LiDAR–inertial odometry + loop closure) for the outdoor bot.

Uses sim/robot topics:

| Topic | Message | Frame |
|-------|---------|-------|
| `/lidar/points` | `sensor_msgs/PointCloud2` | `lidar_link` |
| `/imu/data` | `sensor_msgs/Imu` | `imu_link` |

LIO-SAM expects Velodyne-style clouds (`ring` + `time` fields). `velodyne_cloud_adapter` converts Gazebo `/lidar/points` → `/lio_sam/points`.

Config: `config/lio_sam_params.yaml` (Unitree L2 as **39 × 591** Velodyne grid, extrinsics lidar↔IMU).

---

## 1. Install LIO-SAM (once per machine)

**ROS 2 Jazzy / Ubuntu 24.04:** upstream targets Humble; on Jazzy you may need **GTSAM 4.0/4.1 built from source** if apt installs a newer version ([issue #563](https://github.com/TixiaoShan/LIO-SAM/issues/563)).

```bash
# ROS deps
sudo apt install -y \
  ros-jazzy-perception-pcl \
  ros-jazzy-pcl-msgs \
  ros-jazzy-vision-opencv \
  ros-jazzy-xacro \
  libpcl-dev

# GTSAM 4.2 (example; pin version if LIO-SAM fails to link)
sudo apt install -y libgtsam-dev libgtsam-unstable-dev
# If build fails: build GTSAM 4.1 from https://gtsam.org/get_started/

# Clone into this workspace
cd ~/Documents/GITHUB/OUTDOOR_ROBOT
vcs import src < src/bot_mapping/repos/lio_sam.repos
# or: git clone -b ros2 https://github.com/TixiaoShan/LIO-SAM.git src/LIO-SAM

colcon build --packages-select lio_sam --symlink-install
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

## 3. Run mapping in simulation

**Terminal 1 — sim + LIO-SAM + RViz:**

```bash
source install/setup.bash
ros2 launch bot_mapping mapping_sim.launch.py
```

Press **Play** in Gazebo. Drive the robot (teleop in another terminal):

```bash
ros2 launch bot_teleoperation teleop.launch.py use_sim_time:=true
```

**LIO-SAM only** (sim already running):

```bash
ros2 launch bot_mapping lio_sam.launch.py use_sim_time:=true
```

---

## 4. Useful topics

```bash
ros2 topic hz /lio_sam/points -s
ros2 topic hz /lio_sam/mapping/odometry -s
ros2 topic list | grep lio_sam
```

RViz **Fixed Frame**: `map`. Main cloud: `/lio_sam/mapping/map_global`.

---

## 5. Tuning

| File | What to change |
|------|----------------|
| `config/lio_sam_params.yaml` | `N_SCAN`, `Horizon_SCAN`, extrinsics, loop closure |
| `velodyne_cloud_adapter` params | vertical FOV bins if rings look wrong |
| `bot_description/config/unitree_4d_lidar_l2.yaml` | sim lidar grid / mount height |

If mapping is slow, reduce `horizontal_samples` / `vertical_samples` in the lidar yaml (GPU), or set `downsampleRate: 2` in `lio_sam_params.yaml`.

---

## Architecture

```text
/lidar/points (Gazebo) ──► velodyne_cloud_adapter ──► /lio_sam/points
/imu/data ─────────────────────────────────────────► LIO-SAM nodes
robot_state_publisher (sim) ──► TF: base_link, lidar_link, imu_link
LIO-SAM mapOptimization ──► map, odom, /lio_sam/mapping/*
```

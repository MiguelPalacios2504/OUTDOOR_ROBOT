# bot_localization

EKF fusion, wheel odometry, **laser odometry** (`ros2_laser_scan_matcher` → `/laser/odom`), SLAM mapping, and AMCL on saved maps.

Laser odometry belongs here, not in `bot_planning`. The EKF merges `/wheel/odom`, optional `/laser/odom`, and IMU into `/odometry/filtered` for Nav2.

Planning lives in **`bot_planning`** — see `../bot_planning/INTERFACE.md`.

## Launch

```bash
# EKF + wheel odom only
ros2 launch bot_localization localization.launch.py \
  enable_slam:=false enable_saved_map_localization:=false

# Mapping with slam_toolbox
ros2 launch bot_localization localization.launch.py \
  enable_slam:=true enable_saved_map_localization:=false

# Localize in a saved map (for Nav2 / bot_planning)
ros2 launch bot_localization localization.launch.py \
  enable_slam:=false enable_saved_map_localization:=true \
  map_yaml_file:=/path/to/maps/arena_map.yaml
```

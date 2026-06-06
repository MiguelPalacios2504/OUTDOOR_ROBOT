# bot_bringup

Real robot launches.

## Layers

| Launch | What it starts |
|---|---|
| `real_robot.launch.py` | URDF, ros2_control, swerve, firmware mock |
| `real_autonomy.launch.py` | real_robot + sensors + localization + optional Nav2 |

## Quick start (bench, all mocks)

```bash
source install/setup.bash
ros2 launch bot_bringup real_autonomy.launch.py use_rviz:=true
```

## Typical modes

```bash
# 1 — only base robot + control
ros2 launch bot_bringup real_robot.launch.py

# 2 — full stack with saved map + Nav2
ros2 launch bot_bringup real_autonomy.launch.py \\
  use_mock_firmware:=false use_mock_sensors:=false \\
  enable_navigation:=true use_rviz:=true

# 3 — outdoor mapping (SLAM)
ros2 launch bot_bringup real_autonomy.launch.py \\
  enable_slam:=true enable_saved_map_localization:=false \\
  enable_navigation:=false use_rviz:=true

# 4 — GPS fusion (needs real /gps/fix)
ros2 launch bot_bringup real_autonomy.launch.py enable_gps:=true
```

Simulación sin cambios: `ros2 launch bot_gazebo simulation.launch.py`

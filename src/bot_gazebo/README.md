# bot_gazebo

Gazebo Sim, robot spawn, `ros2_control`, sensor bridges (lidar + camera), and swerve command stack.

**Does not** start localization, SLAM, AMCL, or Nav2 — use `bot_localization` and `bot_planning` in separate terminals.

## Terminal 1 — simulation

```bash
source install/setup.bash
ros2 launch bot_gazebo sim_swerve.launch.py
```

Optional: `use_lidar:=false`, `use_camera:=false` if you need a lighter sim.

## Terminal 2 — localization

```bash
source install/setup.bash
ros2 launch bot_localization localization.launch.py \
  enable_slam:=false \
  enable_saved_map_localization:=true \
  enable_laser_odometry:=true \
  map_yaml_file:=$(pwd)/maps/arena_map.yaml
```

For mapping: `enable_slam:=true enable_saved_map_localization:=false`

## Terminal 3 — planning (after AMCL + map are running)

```bash
source install/setup.bash
ros2 launch bot_planning navigation.launch.py use_sim_time:=true
```

## Terminal 4 — RViz (optional)

```bash
ros2 launch bot_localization localization_rviz.launch.py
```

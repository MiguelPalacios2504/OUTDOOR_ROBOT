# bot_gazebo

Gazebo Sim, robot spawn, `ros2_control`, sensor bridges (3D lidar + camera), and swerve control.

3D LiDAR simulates a **Unitree 4D-LiDAR L2** (360° × 96° FOV, 0.05–30 m) and publishes `sensor_msgs/PointCloud2` on `/lidar/points`.

## Launch

```bash
source install/setup.bash
ros2 launch bot_gazebo sim_swerve.launch.py
```

Optional: `use_lidar:=false`, `use_camera:=false` for a lighter sim.

Config defaults: `config/sim_swerve.yaml`.

# bot_gazebo

Gazebo Sim, robot spawn, `ros2_control`, sensor bridges (3D lidar + camera), and swerve control.

3D LiDAR: **Unitree 4D-LiDAR L2** parameters from `bot_description/config/unitree_4d_lidar_l2.yaml` (manufacturer datasheet). Publishes `sensor_msgs/PointCloud2` on `/lidar/points` at 5.55 Hz (~591×39 rays ≈ 128k pts/s).

## Launch

```bash
source install/setup.bash
ros2 launch bot_gazebo sim_swerve.launch.py
```

Optional: `use_lidar:=false`, `use_camera:=false` for a lighter sim.

Config defaults: `config/sim_swerve.yaml`.

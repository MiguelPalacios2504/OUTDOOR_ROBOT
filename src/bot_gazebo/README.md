# bot_gazebo

Gazebo Sim, robot spawn, `ros2_control`, sensor bridges (lidar + camera), and swerve control.

## Launch

```bash
source install/setup.bash
ros2 launch bot_gazebo sim_swerve.launch.py
```

Optional: `use_lidar:=false`, `use_camera:=false` for a lighter sim.

Config defaults: `config/sim_swerve.yaml`.

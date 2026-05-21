# bot_planning

Nav2 motion planning and control (planner, controller, behaviors, BT navigator).

**Does not** run laser odometry, SLAM, AMCL, or EKF — those live in `bot_localization`.

This stack only consumes:
- `/odometry/filtered` (EKF output, may already include fused wheel + laser + IMU)
- `/map` and TF `map` → `odom` (from localization)
- `/scan` in costmaps (raw laser for obstacles — **not** the same as `/laser/odom`)

See [INTERFACE.md](INTERFACE.md) for the contract with `bot_localization`.

## Launch

```bash
ros2 launch bot_planning navigation.launch.py use_sim_time:=true
```

Configuration: `config/nav2.yaml`.

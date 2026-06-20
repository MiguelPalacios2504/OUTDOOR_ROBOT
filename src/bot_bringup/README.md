# bot_bringup

Launches para el robot real.

## Teleop (recomendado para empezar)

Ver guía completa: [`../../TELEOP.md`](../../TELEOP.md)

```bash
# Scripts (recomendado)
~/OUTDOOR_ROBOT/microros/scripts/run_agent.sh              # terminal 1
~/OUTDOOR_ROBOT/microros/scripts/run_teleop_keyboard.sh    # terminal 2

# O launch ROS (teclado en terminal aparte)
ros2 launch bot_bringup teleop_real.launch.py
ros2 run teleop_twist_keyboard teleop_twist_keyboard      # otra terminal
```

## Layers

| Launch | What it starts |
|---|---|
| `teleop_real.launch.py` | micro-ROS agent + puente `/cmd_vel` → `/hw/joint_commands` |
| `real_robot.launch.py` | URDF, ros2_control, swerve, firmware mock |
| `real_autonomy.launch.py` | real_robot + sensors + localization + optional Nav2 |

## Typical modes (avanzado)

```bash
# Base robot + ros2_control
ros2 launch bot_bringup real_robot.launch.py use_mock_firmware:=false

# Full stack + Nav2
ros2 launch bot_bringup real_autonomy.launch.py \\
  use_mock_firmware:=false use_mock_sensors:=false \\
  enable_navigation:=true use_rviz:=true
```

Simulación: `ros2 launch bot_gazebo simulation.launch.py`

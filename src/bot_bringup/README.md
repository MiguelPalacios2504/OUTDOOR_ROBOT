# bot_bringup

**Solo robot real.**

```bash
source install/setup.bash
ros2 launch bot_bringup real_robot.launch.py
```

`real_robot.launch.py` levanta URDF real, `ros2_control`, controllers, swerve control y (por defecto) `hw_firmware_mock` para probar sin ESP32.

Alias: `ros2 launch bot_bringup bringup.launch.py`

Argumentos útiles:

- `use_mock_firmware:=false` — cuando la ESP32/micro-ROS publique `/hw/joint_states`
- `use_rviz:=true` — visualización opcional

Simulación → `bot_gazebo`. Localización → `bot_localization`. Navegación → `bot_planning`.

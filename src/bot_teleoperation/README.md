# bot_teleoperation

Holonomic keyboard teleop for the outdoor bot (4WIS swerve). Publishes `geometry_msgs/msg/Twist` on `/cmd_vel` (`linear.x`, `linear.y`, `angular.z`).

## Controls

| Action | Keys |
|--------|------|
| Forward / back | `w` / `s` or ↑ / ↓ |
| Strafe left / right | `a` / `d` or ← / → |
| Rotate CCW / CW (Z) | `q` / `e` or `z` / `c` |
| Diagonal | p. ej. `w` luego `a` (acumula pasos en X e Y) |
| Girar en movimiento | p. ej. `w` + `q` |
| Parar todo | `x` |
| Paso lineal | `+` / `-` |
| Paso angular | `[` / `]` |
| Toggle sticky / hold | `t` (solo `control_mode:=absolute`) |

**Incremental (default):** cada `w` suma `linear_step` a vx (hasta `max_linear_x`). `s` resta. `x` para todo. Igual que `ros2 run bot_teleoperation keyboard_teleop_node`.

**Absolute** (`control_mode:=absolute`): una tecla = velocidad máxima en ese eje.

With `holonomic_normalize: true`, diagonals keep direction but cap speed so combined X+Y is not faster than the linear limit alone.

## Usage

**Terminal 1 — simulation**

```bash
ros2 launch bot_gazebo sim_swerve.launch.py
```

**Terminal 2 — teleop** (real terminal, focus here)

```bash
ros2 launch bot_teleoperation teleop.launch.py use_sim_time:=true
```

Or:

```bash
ros2 run bot_teleoperation keyboard_teleop_node --ros-args -p use_sim_time:=true
```

## Parameters

See `config/teleop.yaml`. Key ones:

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `control_mode` | `incremental` | `incremental` or `absolute` |
| `linear_step` | `0.05` | m/s added per translation key press |
| `angular_step` | `0.1` | rad/s added per rotation key press |
| `max_linear_x/y` | `0.5` | velocity clamp per axis |

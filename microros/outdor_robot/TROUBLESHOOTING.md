# micro-ROS troubleshooting (Pi + ESP32)

## Correct startup order

Use **two terminals**.

**Terminal 1 — agent (leave running):**
```bash
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
source /opt/ros/jazzy/setup.bash
ros2 daemon stop
ros2 daemon start
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 -b 115200 -v6
```

Wait until you see logs like `create_publisher`, `create_subscriber`, or `session established`.

**Terminal 2 — check topics (same env vars):**
```bash
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
source /opt/ros/jazzy/setup.bash
ros2 node list
ros2 topic list
ros2 topic echo /hw/joint_states
```

If topics still missing, **press RESET on the ESP32** while the agent is running.

---

## Checklist

| Check | Command / action |
|-------|------------------|
| Port exists | `ls -l /dev/ttyUSB*` |
| Permissions | `sudo chmod 666 /dev/ttyUSB0` |
| Same domain ID | `echo $ROS_DOMAIN_ID` → should be `0` in **both** terminals |
| Agent package | `ros2 pkg list \| grep micro_ros_agent` |
| Node visible | `ros2 node list` → `/outdoor_robot_firmware` |
| Message type | `ros2 topic info /hw/joint_states -v` → `Float64MultiArray` |
| No serial monitor | Close PlatformIO Monitor while agent runs |
| Firmware distro | `board_microros_distro = jazzy` in platformio.ini |

---

## Agent log should show

When ESP32 connects you should see something like:
```
create_publisher ... hw/joint_states
create_subscription ... hw/joint_commands
```

If you only see ping/heartbeat but **no create_publisher**, the ESP32 did not finish `setup_micro_ros()`. Reflash firmware and reset the board.

---

## Manual test (Terminal 2)

```bash
ros2 topic pub -r 10 /hw/joint_commands std_msgs/msg/Float64MultiArray \
  "{data: [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0]}"
```

---

## Common mistakes

1. **Reading topics in the same terminal as the agent** — agent blocks that shell; open a second terminal.
2. **Different `ROS_DOMAIN_ID`** — agent sees topics, your `ros2 topic list` does not. Fix: `export ROS_DOMAIN_ID=0` everywhere, or `unset ROS_DOMAIN_ID`.
3. **Agent started before ESP32 flashed with jazzy firmware** — reflash, then reset ESP32 with agent running.
4. **Float32 vs Float64** — Pi expects `Float64MultiArray`; firmware must match.

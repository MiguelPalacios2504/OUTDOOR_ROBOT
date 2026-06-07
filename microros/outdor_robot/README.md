# outdoor_robot micro-ROS firmware

Implements the same topic contract as `bot_hardware_interface` and `hw_firmware_mock`.

## Upload

```bash
sudo chmod 666 /dev/ttyUSB0
pio run -t upload
```

If you changed ROS distro, clean micro-ROS first:

```bash
pio run --target clean_microros
pio run -t upload
```

## Run micro-ROS agent (on the PC)

With the ESP32 flashed and connected on `/dev/ttyUSB0`:

```bash
docker run -it --rm -v /dev:/dev -v /dev/shm:/dev/shm --privileged --net=host \
  microros/micro-ros-agent:jazzy serial --dev /dev/ttyUSB0 -b 115200 -v6
```

Adjust the ROS distro tag to match your workspace (this project uses **jazzy**).

Do not open the serial monitor while the agent is running.

## Topics

| Topic | Type | Direction | Rate |
|-------|------|-----------|------|
| `/hw/joint_commands` | `std_msgs/Float64MultiArray` | ROS 2 → ESP32 | ~100 Hz |
| `/hw/joint_states` | `std_msgs/Float64MultiArray` | ESP32 → ROS 2 | 100 Hz |

### Array layout (8 values)

| Index | Joint | Unit | ESP32 mapping |
|-------|-------|------|---------------|
| 0–3 | steering joints | rad | ignored (no servos yet) |
| 4 | `f_leftwheel` | rad/s | **motor 1** setpoint / feedback |
| 5 | `f_rightwheel` | rad/s | **motor 2** setpoint / feedback |
| 6–7 | rear wheels | rad/s | not connected (always 0) |

## Use with ros2_control

Launch the real robot stack without the mock:

```bash
ros2 launch bot_bringup real_robot.launch.py use_mock_firmware:=false
```

## Manual test

```bash
# Send wheel velocities (indices 4 and 5 = 1.0 rad/s each)
ros2 topic pub /hw/joint_commands std_msgs/msg/Float64MultiArray \
  "{data: [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0]}"

# Read measured velocities
ros2 topic echo /hw/joint_states
```



https://github.com/micro-ROS/micro_ros_platformio/blob/main/examples/micro-ros_publisher/src/Main.cpp
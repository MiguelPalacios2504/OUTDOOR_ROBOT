"""Minimal real-robot teleop over micro-ROS.

Starts:
  - micro-ROS serial agent (ESP32 on /dev/ttyUSB0)
  - teleop_joint_commands_node  (/cmd_vel -> /hw/joint_commands)
  - teleop input (keyboard or joystick)

No Gazebo, no Nav2, no ros2_control.

Prerequisites:
  1. Flash outdoor_robot firmware to the ESP32 (PlatformIO, env esp32dev).
  2. Source ROS and workspaces:
       source /opt/ros/jazzy/setup.bash
       source ~/uros_ws/install/setup.bash      # micro_ros_agent
       source ~/OUTDOOR_ROBOT/install/setup.bash
  3. ESP32 connected on the serial port (default /dev/ttyUSB0).

Usage:
  # Keyboard teleop (default)
  ros2 launch bot_bringup teleop_real.launch.py

  # Joystick teleop
  ros2 launch bot_bringup teleop_real.launch.py teleop:=joy

  # Agent already running in another terminal
  ros2 launch bot_bringup teleop_real.launch.py run_agent:=false
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    bot_control = get_package_share_directory("bot_control")

    serial_port = LaunchConfiguration("serial_port")
    run_agent = LaunchConfiguration("run_agent")
    teleop = LaunchConfiguration("teleop")
    use_sim_time = LaunchConfiguration("use_sim_time")

    use_keyboard = PythonExpression(["'", teleop, "' == 'keyboard'"])
    use_joy = PythonExpression(["'", teleop, "' == 'joy'"])

    micro_ros_agent = Node(
        package="micro_ros_agent",
        executable="micro_ros_agent",
        name="micro_ros_agent",
        arguments=["serial", "--dev", serial_port, "-b", "115200", "-v4"],
        output="screen",
        condition=IfCondition(run_agent),
    )

    teleop_bridge = Node(
        package="bot_control",
        executable="teleop_joint_commands_node",
        name="teleop_joint_commands_node",
        output="screen",
        parameters=[
            os.path.join(bot_control, "config", "teleop_joint_commands.yaml"),
            {"use_sim_time": use_sim_time},
        ],
    )

    keyboard_teleop = Node(
        package="teleop_twist_keyboard",
        executable="teleop_twist_keyboard",
        name="teleop_twist_keyboard",
        output="screen",
        condition=IfCondition(use_keyboard),
    )

    joy_node = Node(
        package="joy",
        executable="joy_node",
        name="joy_node",
        output="screen",
        parameters=[{"autorepeat_rate": 20.0}],
        condition=IfCondition(use_joy),
    )

    joy_teleop = Node(
        package="teleop_twist_joy",
        executable="teleop_node",
        name="teleop_twist_joy_node",
        output="screen",
        parameters=[
            {
                "axis_linear.x": 1,
                "axis_angular.yaw": 0,
                "scale_linear.x": 0.5,
                "scale_angular.yaw": -1.0,
                "require_enable_button": False,
            }
        ],
        condition=IfCondition(use_joy),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "serial_port",
                default_value="/dev/ttyUSB0",
                description="Serial port for the ESP32 micro-ROS connection.",
            ),
            DeclareLaunchArgument(
                "run_agent",
                default_value="true",
                description="Start micro_ros_agent in this launch.",
            ),
            DeclareLaunchArgument(
                "teleop",
                default_value="none",
                description="Teleop input: none, keyboard, or joy. "
                "Prefer run_teleop_keyboard.sh in a separate interactive terminal.",
                choices=["none", "keyboard", "joy"],
            ),
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
            ),
            micro_ros_agent,
            teleop_bridge,
            keyboard_teleop,
            joy_node,
            joy_teleop,
        ]
    )

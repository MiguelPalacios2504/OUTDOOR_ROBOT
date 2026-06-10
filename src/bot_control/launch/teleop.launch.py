"""Teleop simple: teclado -> /cmd_vel -> /hw/joint_commands."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    bot_control = get_package_share_directory("bot_control")
    run_keyboard = LaunchConfiguration("run_keyboard")

    return LaunchDescription(
        [
            DeclareLaunchArgument("run_keyboard", default_value="false"),
            Node(
                package="bot_control",
                executable="teleop_joint_commands_node",
                output="screen",
                parameters=[
                    os.path.join(bot_control, "config", "teleop_joint_commands.yaml"),
                ],
            ),
            Node(
                package="teleop_twist_keyboard",
                executable="teleop_twist_keyboard",
                output="screen",
                condition=IfCondition(run_keyboard),
            ),
        ]
    )

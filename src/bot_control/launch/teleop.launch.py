

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    bot_control = get_package_share_directory("bot_control")
    use_sim_time = LaunchConfiguration("use_sim_time")
    run_keyboard = LaunchConfiguration("run_keyboard")

    return LaunchDescription(
        [
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            DeclareLaunchArgument(
                "run_keyboard",
                default_value="false",
                description="Launch teleop_twist_keyboard (publishes /cmd_vel).",
            ),
            Node(
                package="bot_control",
                executable="teleop_joint_commands_node",
                name="teleop_joint_commands_node",
                output="screen",
                parameters=[
                    os.path.join(bot_control, "config", "teleop_joint_commands.yaml"),
                    {"use_sim_time": use_sim_time},
                ],
            ),
            Node(
                package="teleop_twist_keyboard",
                executable="teleop_twist_keyboard",
                name="teleop_twist_keyboard",
                output="screen",
                condition=IfCondition(run_keyboard),
            ),
        ]
    )












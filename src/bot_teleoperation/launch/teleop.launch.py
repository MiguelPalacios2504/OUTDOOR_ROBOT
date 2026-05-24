from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_share = Path(get_package_share_directory("bot_teleoperation"))
    config_path = package_share / "config" / "teleop.yaml"

    use_sim_time = LaunchConfiguration("use_sim_time")
    cmd_vel_topic = LaunchConfiguration("cmd_vel_topic")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use simulation clock when driving the robot in Gazebo.",
            ),
            DeclareLaunchArgument(
                "cmd_vel_topic",
                default_value="/cmd_vel",
                description="Twist topic consumed by bot_control swerve_cmd_node.",
            ),
            Node(
                package="bot_teleoperation",
                executable="keyboard_teleop_node",
                name="keyboard_teleop_node",
                output="screen",
                emulate_tty=True,
                parameters=[
                    str(config_path),
                    {
                        "use_sim_time": use_sim_time,
                        "cmd_vel_topic": cmd_vel_topic,
                    },
                ],
            ),
        ]
    )

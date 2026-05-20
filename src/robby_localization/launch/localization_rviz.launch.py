from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    localization_share = Path(get_package_share_directory("robby_localization"))
    rviz_config = str(localization_share / "rviz" / "localization.rviz")
    use_sim_time = LaunchConfiguration("use_sim_time")
    config_file = LaunchConfiguration("rviz_config")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="true",
                description="Use simulation time in RViz.",
            ),
            DeclareLaunchArgument(
                "rviz_config",
                default_value=rviz_config,
                description="Absolute path to the RViz config file.",
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                name="rviz2_localization",
                output="screen",
                arguments=["-d", config_file],
                parameters=[{"use_sim_time": use_sim_time}],
            ),
        ]
    )

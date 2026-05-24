from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    gazebo_share = Path(get_package_share_directory("bot_gazebo"))
    mapping_share = Path(get_package_share_directory("bot_mapping"))

    use_sim_time = LaunchConfiguration("use_sim_time")

    sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(gazebo_share / "launch" / "sim_swerve.launch.py")),
    )

    lio_sam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(mapping_share / "launch" / "lio_sam.launch.py")),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "use_rviz": "true",
        }.items(),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="true",
                description="Simulation clock for Gazebo + LIO-SAM.",
            ),
            sim_launch,
            lio_sam_launch,
        ]
    )

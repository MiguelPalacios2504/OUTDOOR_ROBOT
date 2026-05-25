import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    mapping_share = Path(get_package_share_directory("bot_mapping"))
    fast_lio_share = get_package_share_directory("fast_lio")

    config_path = str(mapping_share / "config")
    rviz_config = str(mapping_share / "rviz" / "mapping_fast_lio.rviz")

    use_sim_time = LaunchConfiguration("use_sim_time")
    use_rviz = LaunchConfiguration("use_rviz")
    use_lidar_adapter = LaunchConfiguration("use_lidar_adapter")
    config_file = LaunchConfiguration("config_file")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use simulation clock from Gazebo.",
            ),
            DeclareLaunchArgument(
                "use_rviz",
                default_value="false",
                description=(
                    "Start bot_mapping RViz (mapping_fast_lio.rviz). "
                    "Default off; use bot_gazebo sim_rviz.launch.py for sim_lidar.rviz."
                ),
            ),
            DeclareLaunchArgument(
                "use_lidar_adapter",
                default_value="true",
                description=(
                    "Add ring/time fields to Gazebo PointCloud2 for FAST-LIO Velodyne handler."
                ),
            ),
            DeclareLaunchArgument(
                "config_file",
                default_value="fast_lio_unitree_l2.yaml",
                description="FAST-LIO YAML (use fast_lio_unitree_l2_direct.yaml without adapter).",
            ),
            LogInfo(
                msg=(
                    "FAST-LIO2 mapping: requires fast_lio built in the workspace "
                    "(see bot_mapping/README.md)."
                )
            ),
            Node(
                package="bot_mapping",
                executable="unitree_lidar_adapter",
                name="unitree_lidar_adapter",
                output="screen",
                condition=IfCondition(use_lidar_adapter),
                parameters=[
                    {
                        "use_sim_time": use_sim_time,
                        "input_topic": "/lidar/points",
                        "output_topic": "/fast_lio/points",
                        "n_scan": 39,
                        "vertical_min_deg": -8.0,
                        "vertical_max_deg": 90.0,
                        "scan_rate_hz": 5.55,
                    }
                ],
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(fast_lio_share, "launch", "mapping.launch.py")
                ),
                launch_arguments={
                    "use_sim_time": use_sim_time,
                    "config_path": config_path,
                    "config_file": config_file,
                    "rviz": "false",
                }.items(),
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                name="rviz2",
                arguments=["-d", rviz_config],
                parameters=[{"use_sim_time": use_sim_time}],
                condition=IfCondition(use_rviz),
                output="screen",
            ),
        ]
    )

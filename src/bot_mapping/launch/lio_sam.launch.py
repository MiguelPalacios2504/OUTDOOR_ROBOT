import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    mapping_share = Path(get_package_share_directory("bot_mapping"))
    params_file = str(mapping_share / "config" / "lio_sam_params.yaml")
    rviz_config = str(mapping_share / "rviz" / "mapping_lio_sam.rviz")

    use_sim_time = LaunchConfiguration("use_sim_time")
    use_rviz = LaunchConfiguration("use_rviz")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use simulation clock from Gazebo.",
            ),
            DeclareLaunchArgument(
                "use_rviz",
                default_value="true",
                description="Start RViz with LIO-SAM mapping view.",
            ),
            DeclareLaunchArgument(
                "params_file",
                default_value=params_file,
                description="LIO-SAM parameter file for the outdoor bot.",
            ),
            LogInfo(msg="LIO-SAM mapping: requires lio_sam built in the workspace (see bot_mapping/README.md)."),
            Node(
                package="tf2_ros",
                executable="static_transform_publisher",
                name="map_to_odom",
                arguments=["0", "0", "0", "0", "0", "0", "map", "odom"],
                parameters=[{"use_sim_time": use_sim_time}],
                output="screen",
            ),
            Node(
                package="bot_mapping",
                executable="velodyne_cloud_adapter",
                name="velodyne_cloud_adapter",
                output="screen",
                parameters=[
                    {
                        "use_sim_time": use_sim_time,
                        "input_topic": "/lidar/points",
                        "output_topic": "/lio_sam/points",
                        "n_scan": 39,
                        "vertical_min_deg": -8.0,
                        "vertical_max_deg": 90.0,
                    }
                ],
            ),
            Node(
                package="lio_sam",
                executable="lio_sam_imuPreintegration",
                name="lio_sam_imuPreintegration",
                parameters=[LaunchConfiguration("params_file"), {"use_sim_time": use_sim_time}],
                output="screen",
            ),
            Node(
                package="lio_sam",
                executable="lio_sam_imageProjection",
                name="lio_sam_imageProjection",
                parameters=[LaunchConfiguration("params_file"), {"use_sim_time": use_sim_time}],
                output="screen",
            ),
            Node(
                package="lio_sam",
                executable="lio_sam_featureExtraction",
                name="lio_sam_featureExtraction",
                parameters=[LaunchConfiguration("params_file"), {"use_sim_time": use_sim_time}],
                output="screen",
            ),
            Node(
                package="lio_sam",
                executable="lio_sam_mapOptimization",
                name="lio_sam_mapOptimization",
                parameters=[LaunchConfiguration("params_file"), {"use_sim_time": use_sim_time}],
                output="screen",
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

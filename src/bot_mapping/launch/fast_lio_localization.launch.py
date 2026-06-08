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
    repo_root = mapping_share.parent.parent.parent

    default_map = str(repo_root / "maps" / "mi_mapa_sim.pcd")
    config_path = str(mapping_share / "config")
    rviz_config = str(mapping_share / "rviz" / "localization_fast_lio.rviz")

    use_sim_time = LaunchConfiguration("use_sim_time")
    use_rviz = LaunchConfiguration("use_rviz")
    use_lidar_adapter = LaunchConfiguration("use_lidar_adapter")
    use_robot_tf_bridge = LaunchConfiguration("use_robot_tf_bridge")
    config_file = LaunchConfiguration("config_file")
    pcd_map_path = LaunchConfiguration("pcd_map_path")

    localization_params = [
        {"use_sim_time": use_sim_time},
        {"pcd_map_path": pcd_map_path},
        {"map_voxel_size": 0.4},
        {"scan_voxel_size": 0.1},
        {"freq_localization": 0.5},
        {"localization_threshold": 0.8},
        {"fov": 6.28319},
        {"fov_far": 30.0},
    ]

    map_viz_params = [
        {"use_sim_time": use_sim_time},
        {"pcd_map_path": pcd_map_path},
        {"map_topic": "/map"},
        {"map_frame": "map"},
        {"publish_hz": 0.5},
        {"viz_voxel_size": 0.0},
    ]

    return LaunchDescription(
        [
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            DeclareLaunchArgument(
                "use_rviz",
                default_value="false",
                description="Use bot_gazebo sim_rviz.launch.py for visualization.",
            ),
            DeclareLaunchArgument("use_lidar_adapter", default_value="true"),
            DeclareLaunchArgument(
                "use_robot_tf_bridge",
                default_value="true",
                description="Bridge /localization (map frame) to base_footprint for RobotModel.",
            ),
            DeclareLaunchArgument(
                "config_file",
                default_value="fast_lio_localization.yaml",
            ),
            DeclareLaunchArgument(
                "pcd_map_path",
                default_value=default_map,
                description="Saved PCD map (used as-is; no offline preprocessing).",
            ),
            LogInfo(msg="3D localization: FAST-LIO odom + ICP against saved PCD map."),
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
                package="bot_mapping",
                executable="pcd_map_publisher",
                name="pcd_map_publisher",
                output="screen",
                parameters=map_viz_params,
            ),
            Node(
                package="bot_mapping",
                executable="global_localization",
                name="global_localization",
                output="screen",
                parameters=localization_params,
            ),
            Node(
                package="bot_mapping",
                executable="transform_fusion",
                name="transform_fusion",
                output="screen",
                parameters=[{"use_sim_time": use_sim_time}],
            ),
            Node(
                package="bot_mapping",
                executable="fast_lio_robot_tf_bridge",
                name="fast_lio_robot_tf_bridge",
                output="screen",
                condition=IfCondition(use_robot_tf_bridge),
                parameters=[
                    {
                        "use_sim_time": use_sim_time,
                        "odom_topic": "/localization",
                        "map_frame": "map",
                    }
                ],
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

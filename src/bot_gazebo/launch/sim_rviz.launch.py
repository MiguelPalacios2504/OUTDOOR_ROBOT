import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import LogInfo
from launch_ros.actions import Node


def generate_launch_description():
    gazebo_share = get_package_share_directory("bot_gazebo")
    rviz_config = os.path.join(gazebo_share, "rviz", "sim_lidar.rviz")

    return LaunchDescription(
        [
            LogInfo(
                msg=(
                    "sim_rviz: Lidar3D /lidar/points, Laser_map, SavedMap /map (from "
                    "fast_lio_localization). Use 2D Pose Estimate -> /initialpose."
                )
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                name="rviz2",
                output="screen",
                arguments=["-d", rviz_config],
                parameters=[{"use_sim_time": True}],
            ),
        ]
    )

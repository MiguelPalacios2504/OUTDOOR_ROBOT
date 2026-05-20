from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LifecycleNode, Node


def generate_launch_description():
    localization_share = Path(get_package_share_directory("robby_localization"))
    bt_navigator_share = Path(get_package_share_directory("nav2_bt_navigator"))

    params_file = LaunchConfiguration("params_file")
    default_nav_to_pose_bt_xml = LaunchConfiguration("default_nav_to_pose_bt_xml")
    default_nav_through_poses_bt_xml = LaunchConfiguration("default_nav_through_poses_bt_xml")

    nav2_params = str(localization_share / "config" / "nav2.yaml")
    nav_to_pose_bt_xml = str(
        bt_navigator_share / "behavior_trees" / "navigate_to_pose_w_replanning_and_recovery.xml"
    )
    nav_through_poses_bt_xml = str(
        bt_navigator_share
        / "behavior_trees"
        / "navigate_through_poses_w_replanning_and_recovery.xml"
    )

    planner_server = LifecycleNode(
        package="nav2_planner",
        executable="planner_server",
        name="planner_server",
        namespace="",
        output="screen",
        parameters=[params_file],
    )

    controller_server = LifecycleNode(
        package="nav2_controller",
        executable="controller_server",
        name="controller_server",
        namespace="",
        output="screen",
        parameters=[params_file],
    )

    behavior_server = LifecycleNode(
        package="nav2_behaviors",
        executable="behavior_server",
        name="behavior_server",
        namespace="",
        output="screen",
        parameters=[params_file],
    )

    bt_navigator = LifecycleNode(
        package="nav2_bt_navigator",
        executable="bt_navigator",
        name="bt_navigator",
        namespace="",
        output="screen",
        parameters=[
            params_file,
            {
                "default_nav_to_pose_bt_xml": default_nav_to_pose_bt_xml,
                "default_nav_through_poses_bt_xml": default_nav_through_poses_bt_xml,
            },
        ],
    )

    lifecycle_manager_navigation = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_navigation",
        output="screen",
        parameters=[
            {
                "use_sim_time": True,
                "autostart": True,
                "bond_timeout": 0.0,
                "node_names": [
                    "planner_server",
                    "controller_server",
                    "behavior_server",
                    "bt_navigator",
                ],
            }
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "params_file",
                default_value=nav2_params,
                description="Absolute path to the Nav2 parameter YAML file.",
            ),
            DeclareLaunchArgument(
                "default_nav_to_pose_bt_xml",
                default_value=nav_to_pose_bt_xml,
                description="Behavior tree XML used for NavigateToPose goals.",
            ),
            DeclareLaunchArgument(
                "default_nav_through_poses_bt_xml",
                default_value=nav_through_poses_bt_xml,
                description="Behavior tree XML used for NavigateThroughPoses goals.",
            ),
            planner_server,
            controller_server,
            behavior_server,
            bt_navigator,
            lifecycle_manager_navigation,
        ]
    )

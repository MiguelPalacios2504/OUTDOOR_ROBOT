from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import LifecycleNode, Node
from launch_ros.event_handlers import OnStateTransition
from launch_ros.actions import LifecycleTransition
from lifecycle_msgs.msg import Transition


def config_is_true(config: LaunchConfiguration) -> PythonExpression:
    return PythonExpression(["'", config, "' == 'true'"])


def config_is_false(config: LaunchConfiguration) -> PythonExpression:
    return PythonExpression(["'", config, "' != 'true'"])


def all_configs(*conditions: PythonExpression) -> PythonExpression:
    expression = []
    for index, condition in enumerate(conditions):
        if index > 0:
            expression.append(" and ")
        expression.append(condition)
    return PythonExpression(expression)


def generate_launch_description():
    localization_share = Path(get_package_share_directory("robby_localization"))
    enable_laser_odometry = LaunchConfiguration("enable_laser_odometry")
    enable_slam = LaunchConfiguration("enable_slam")
    enable_saved_map_localization = LaunchConfiguration("enable_saved_map_localization")
    map_yaml_file = LaunchConfiguration("map_yaml_file")
    localization_params = str(localization_share / "config" / "localization.yaml")
    default_map_yaml = str(localization_share / "maps" / "arena_map.yaml")
    slam_condition = IfCondition(
        all_configs(
            config_is_true(enable_slam),
            config_is_false(enable_saved_map_localization),
        )
    )
    saved_map_localization_condition = IfCondition(config_is_true(enable_saved_map_localization))

    localization_input = Node(
        package="robby_localization",
        executable="localization_input_node",
        name="localization_input_node",
        output="screen",
        parameters=[localization_params],
    )

    laser_odometry = Node(
        package="ros2_laser_scan_matcher",
        executable="laser_scan_matcher",
        name="laser_odometry_node",
        output="screen",
        condition=IfCondition(enable_laser_odometry),
        parameters=[localization_params],
    )

    ekf_with_laser = Node(
        package="robot_localization",
        executable="ekf_node",
        name="ekf_filter_node",
        output="screen",
        condition=IfCondition(enable_laser_odometry),
        parameters=[localization_params],
    )

    ekf_without_laser = Node(
        package="robot_localization",
        executable="ekf_node",
        name="ekf_filter_node",
        output="screen",
        condition=UnlessCondition(enable_laser_odometry),
        parameters=[
            localization_params,
            {
                "odom1": "",
                "odom1_config": [
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                ],
            },
        ],
    )

    slam_toolbox_node = LifecycleNode(
        package="slam_toolbox",
        executable="async_slam_toolbox_node",
        name="slam_toolbox",
        namespace="",
        output="screen",
        condition=slam_condition,
        parameters=[localization_params],
    )

    configure_slam = LifecycleTransition(
        lifecycle_node_names=["/slam_toolbox"],
        transition_ids=[Transition.TRANSITION_CONFIGURE],
        condition=slam_condition,
    )

    activate_slam_on_inactive = RegisterEventHandler(
        OnStateTransition(
            target_lifecycle_node=slam_toolbox_node,
            goal_state="inactive",
            entities=[
                LifecycleTransition(
                    lifecycle_node_names=["/slam_toolbox"],
                    transition_ids=[Transition.TRANSITION_ACTIVATE],
                )
            ],
        ),
        condition=slam_condition,
    )

    map_server = LifecycleNode(
        package="nav2_map_server",
        executable="map_server",
        name="map_server",
        namespace="",
        output="screen",
        condition=saved_map_localization_condition,
        parameters=[
            localization_params,
            {
                "yaml_filename": map_yaml_file,
            },
        ],
    )

    amcl = LifecycleNode(
        package="nav2_amcl",
        executable="amcl",
        name="amcl",
        namespace="",
        output="screen",
        condition=saved_map_localization_condition,
        parameters=[localization_params],
    )

    lifecycle_manager_localization = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_localization",
        output="screen",
        condition=saved_map_localization_condition,
        parameters=[
            {
                "use_sim_time": True,
                "autostart": True,
                "bond_timeout": 0.0,
                "node_names": ["map_server", "amcl"],
            }
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "enable_laser_odometry",
                default_value="true",
                description="Start laser odometry and fuse /laser/odom into the EKF.",
            ),
            DeclareLaunchArgument(
                "enable_slam",
                default_value="false",
                description="Start slam_toolbox mapping from /scan.",
            ),
            DeclareLaunchArgument(
                "enable_saved_map_localization",
                default_value="false",
                description=(
                    "Start nav2_map_server + AMCL for saved-map localization. "
                    "When true, this takes over the map -> odom transform instead of slam_toolbox."
                ),
            ),
            DeclareLaunchArgument(
                "map_yaml_file",
                default_value=default_map_yaml,
                description="Absolute path to the occupancy-grid YAML used by nav2_map_server.",
            ),
            localization_input,
            laser_odometry,
            ekf_with_laser,
            ekf_without_laser,
            slam_toolbox_node,
            configure_slam,
            activate_slam_on_inactive,
            map_server,
            amcl,
            lifecycle_manager_localization,
        ]
    )

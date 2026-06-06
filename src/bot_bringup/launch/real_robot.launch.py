"""Real robot bringup: ros2_control + swerve control + optional firmware mock.

Simulation is unchanged — use:
  ros2 launch bot_gazebo simulation.launch.py
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit, OnProcessStart
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    bot_description = get_package_share_directory("bot_description")
    bot_control = get_package_share_directory("bot_control")

    use_sim_time = LaunchConfiguration("use_sim_time")
    use_mock_firmware = LaunchConfiguration("use_mock_firmware")
    use_lidar = LaunchConfiguration("use_lidar")
    use_camera = LaunchConfiguration("use_camera")
    use_rviz = LaunchConfiguration("use_rviz")

    controllers_file = os.path.join(bot_control, "config", "ros2_controllers.yaml")
    urdf_file = os.path.join(bot_description, "urdf", "bot_v1.urdf.xacro")

    robot_description = Command(
        [
            "xacro ",
            urdf_file,
            " mesh_dir:=package://bot_description/meshes",
            " use_lidar:=",
            use_lidar,
            " use_camera:=",
            use_camera,
            " enable_ros2_control:=true",
            " use_hw_topics:=true",
        ]
    )

    load_urdf = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bot_description, "launch", "load_urdf.launch.py")
        ),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "use_lidar": use_lidar,
            "use_camera": use_camera,
            "urdf_file": urdf_file,
            "controllers_file": "",
            "enable_ros2_control": "true",
            "use_hw_topics": "true",
        }.items(),
    )

    ros2_control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        output="screen",
        parameters=[
            {"robot_description": ParameterValue(robot_description, value_type=str)},
            controllers_file,
            {"use_sim_time": use_sim_time},
        ],
    )

    joint_state_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager",
            "/controller_manager",
            "--controller-manager-timeout",
            "30",
        ],
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    steering_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "steering_position_controller",
            "--controller-manager",
            "/controller_manager",
            "--controller-manager-timeout",
            "30",
        ],
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    wheel_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "wheel_velocity_controller",
            "--controller-manager",
            "/controller_manager",
            "--controller-manager-timeout",
            "30",
        ],
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    hw_firmware_mock = Node(
        package="bot_control",
        executable="hw_firmware_mock",
        output="screen",
        condition=IfCondition(use_mock_firmware),
    )

    control = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bot_control, "launch", "control.launch.py")
        ),
        launch_arguments={"use_sim_time": use_sim_time}.items(),
    )

    rviz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bot_description, "launch", "rviz.launch.py")
        ),
        launch_arguments={"use_sim_time": use_sim_time}.items(),
        condition=IfCondition(use_rviz),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use simulation clock (false on real hardware).",
                choices=["true", "True", "false", "False"],
            ),
            DeclareLaunchArgument(
                "use_mock_firmware",
                default_value="true",
                description="Run hw_firmware_mock instead of ESP32/micro-ROS.",
                choices=["true", "True", "false", "False"],
            ),
            DeclareLaunchArgument("use_lidar", default_value="false"),
            DeclareLaunchArgument("use_camera", default_value="false"),
            DeclareLaunchArgument(
                "use_rviz",
                default_value="false",
                choices=["true", "True", "false", "False"],
            ),
            load_urdf,
            hw_firmware_mock,
            ros2_control_node,
            control,
            rviz,
            RegisterEventHandler(
                event_handler=OnProcessStart(
                    target_action=ros2_control_node,
                    on_start=[joint_state_broadcaster],
                )
            ),
            RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=joint_state_broadcaster,
                    on_exit=[steering_controller],
                )
            ),
            RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=joint_state_broadcaster,
                    on_exit=[wheel_controller],
                )
            ),
        ]
    )

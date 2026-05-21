import os
from pathlib import Path
import yaml

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    RegisterEventHandler,
    SetEnvironmentVariable,
)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def load_sim_defaults(gazebo_share: Path) -> dict:
    config_path = gazebo_share / "config" / "sim_swerve.yaml"
    with config_path.open("r", encoding="utf-8") as config_file:
        data = yaml.safe_load(config_file) or {}

    defaults = data.get("sim_swerve", {})
    if not isinstance(defaults, dict):
        raise ValueError(f"sim_swerve section in {config_path} must be a mapping")
    return defaults


def load_unitree_l2_config(description_share: Path) -> dict:
    config_path = description_share / "config" / "unitree_4d_lidar_l2.yaml"
    with config_path.open("r", encoding="utf-8") as config_file:
        data = yaml.safe_load(config_file) or {}

    l2 = data.get("unitree_4d_lidar_l2", {})
    if not isinstance(l2, dict):
        raise ValueError(f"unitree_4d_lidar_l2 section in {config_path} must be a mapping")
    return l2


def unitree_l2_xacro_mappings(l2: dict) -> list[str]:
    gazebo = l2["gazebo"]
    mechanical = l2["mechanical"]
    size_xyz = " ".join(str(v) for v in mechanical["size_xyz_m"])
    return [
        f" lidar_topic:={gazebo['topic']}",
        f" lidar_frame_id:={gazebo['frame_id']}",
        f" lidar_update_rate:={gazebo['update_rate_hz']}",
        f" lidar_horizontal_samples:={gazebo['horizontal_samples']}",
        f" lidar_vertical_samples:={gazebo['vertical_samples']}",
        f" lidar_min_range:={l2['optical']['range_min_m']}",
        f" lidar_max_range:={l2['optical']['range_max_m']}",
        f" lidar_range_resolution:={l2['optical']['range_resolution_m']}",
        f" lidar_noise_stddev:={gazebo['noise_stddev_m']}",
        f' lidar_size_xyz:="{size_xyz}"',
        f" lidar_mass:={mechanical['mass_kg']}",
    ]


def generate_launch_description():
    description_share = Path(get_package_share_directory("bot_description"))
    control_share = Path(get_package_share_directory("bot_control"))
    gazebo_share = Path(get_package_share_directory("bot_gazebo"))
    ros_gz_share = Path(get_package_share_directory("ros_gz_sim"))
    sim_defaults = load_sim_defaults(gazebo_share)
    unitree_l2 = load_unitree_l2_config(description_share)

    xacro_path = description_share / "urdf" / "bot_v1.gazebo.xacro"
    controllers_file = gazebo_share / "config" / "ros2_controllers.yaml"
    world_default = str(
        gazebo_share / "worlds" / str(sim_defaults.get("world_file", "empty.world.sdf"))
    )
    world_file = LaunchConfiguration("world_file")
    use_lidar = LaunchConfiguration("use_lidar")
    use_camera = LaunchConfiguration("use_camera")
    spawn_x = LaunchConfiguration("spawn_x")
    spawn_y = LaunchConfiguration("spawn_y")
    spawn_z = LaunchConfiguration("spawn_z")
    spawn_roll = LaunchConfiguration("spawn_roll")
    spawn_pitch = LaunchConfiguration("spawn_pitch")
    spawn_yaw = LaunchConfiguration("spawn_yaw")

    bot_description = Command(
        [
            "xacro ",
            str(xacro_path),
            " mesh_dir:=",
            "package://bot_description/meshes",
            " controllers_file:=",
            str(controllers_file),
            " use_lidar:=",
            use_lidar,
            " use_camera:=",
            use_camera,
            *unitree_l2_xacro_mappings(unitree_l2),
        ]
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[
            {
                "robot_description": ParameterValue(bot_description, value_type=str),
                "use_sim_time": True,
            }
        ],
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(ros_gz_share / "launch" / "gz_sim.launch.py")),
        launch_arguments={
            "gz_args": ["-r ", world_file],
            "on_exit_shutdown": "true",
        }.items(),
    )

    sim_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="sim_bridge",
        output="screen",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
            "/imu/data@sensor_msgs/msg/Imu[gz.msgs.IMU",
            "/ground_truth/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry",
            "/lidar/points@sensor_msgs/msg/PointCloud2@gz.msgs.PointCloudPacked",
            "/camera/image@sensor_msgs/msg/Image@gz.msgs.Image",
            "/camera/depth_image@sensor_msgs/msg/Image@gz.msgs.Image",
            "/camera/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo",
        ],
    )

    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        name="spawn_robot",
        output="screen",
        parameters=[
            {
                "topic": "/robot_description",
                "name": "bot",
                "allow_renaming": False,
                "x": spawn_x,
                "y": spawn_y,
                "z": spawn_z,
                "R": spawn_roll,
                "P": spawn_pitch,
                "Y": spawn_yaw,
            }
        ],
    )

    joint_state_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
        output="screen",
    )

    steering_position_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["steering_position_controller", "--controller-manager", "/controller_manager"],
        output="screen",
    )

    wheel_velocity_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["wheel_velocity_controller", "--controller-manager", "/controller_manager"],
        output="screen",
    )

    swerve_cmd_node = Node(
        package="bot_control",
        executable="swerve_cmd_node",
        name="swerve_cmd_node",
        output="screen",
        parameters=[str(control_share / "config" / "swerve_cmd.yaml"), {"use_sim_time": True}],
    )

    joint_command_bridge = Node(
        package="bot_control",
        executable="joint_command_bridge",
        name="joint_command_bridge",
        output="screen",
        parameters=[
            str(control_share / "config" / "joint_command_bridge.yaml"),
            {
                "use_sim_time": True,
                "command_topic": "/swerve_cmd_joint_states",
            },
        ],
    )

    resource_roots = [str(description_share.parent), str(gazebo_share.parent)]
    existing_resource_path = os.environ.get("GZ_SIM_RESOURCE_PATH", "")
    gz_resource_path = os.pathsep.join(
        [entry for entry in [*resource_roots, existing_resource_path] if entry]
    )

    set_gz_resource_path = SetEnvironmentVariable(
        name="GZ_SIM_RESOURCE_PATH",
        value=gz_resource_path,
    )

    load_joint_state_broadcaster = RegisterEventHandler(
        OnProcessExit(target_action=spawn_robot, on_exit=[joint_state_broadcaster])
    )
    load_steering_controller = RegisterEventHandler(
        OnProcessExit(target_action=joint_state_broadcaster, on_exit=[steering_position_controller])
    )
    load_wheel_controller = RegisterEventHandler(
        OnProcessExit(target_action=joint_state_broadcaster, on_exit=[wheel_velocity_controller])
    )

    return LaunchDescription(
        [
            set_gz_resource_path,
            DeclareLaunchArgument(
                "use_lidar",
                default_value=str(sim_defaults.get("use_lidar", True)).lower(),
                description="Enable Unitree 4D-LiDAR L2 (datasheet) in URDF and bridge /lidar/points.",
            ),
            DeclareLaunchArgument(
                "use_camera",
                default_value=str(sim_defaults.get("use_camera", True)).lower(),
                description="Enable RGB-D camera in URDF and bridge /camera/* topics.",
            ),
            DeclareLaunchArgument(
                "world_file",
                default_value=world_default,
                description="Absolute path to the Gazebo world file.",
            ),
            DeclareLaunchArgument(
                "spawn_x",
                default_value=str(sim_defaults.get("spawn_x", 0.0)),
                description="Robot spawn x position in the Gazebo world.",
            ),
            DeclareLaunchArgument(
                "spawn_y",
                default_value=str(sim_defaults.get("spawn_y", 0.0)),
                description="Robot spawn y position in the Gazebo world.",
            ),
            DeclareLaunchArgument(
                "spawn_z",
                default_value=str(sim_defaults.get("spawn_z", 0.2)),
                description="Robot spawn z position in the Gazebo world.",
            ),
            DeclareLaunchArgument(
                "spawn_roll",
                default_value=str(sim_defaults.get("spawn_roll", 0.0)),
                description="Robot spawn roll in radians.",
            ),
            DeclareLaunchArgument(
                "spawn_pitch",
                default_value=str(sim_defaults.get("spawn_pitch", 0.0)),
                description="Robot spawn pitch in radians.",
            ),
            DeclareLaunchArgument(
                "spawn_yaw",
                default_value=str(sim_defaults.get("spawn_yaw", 0.0)),
                description="Robot spawn yaw in radians.",
            ),
            gazebo,
            sim_bridge,
            robot_state_publisher,
            spawn_robot,
            load_joint_state_broadcaster,
            load_steering_controller,
            load_wheel_controller,
            swerve_cmd_node,
            joint_command_bridge,
        ]
    )

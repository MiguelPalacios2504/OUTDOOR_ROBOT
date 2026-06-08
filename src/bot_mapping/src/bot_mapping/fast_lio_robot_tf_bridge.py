#!/usr/bin/env python3
"""Connect FAST-LIO map frame (camera_init -> body) to the URDF robot tree."""

from __future__ import annotations

from typing import Optional

import rclpy
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from tf2_ros import TransformBroadcaster


class FastLioRobotTfBridge(Node):
    def __init__(self) -> None:
        super().__init__("fast_lio_robot_tf_bridge")

        self.declare_parameter("odom_topic", "/Odometry")
        self.declare_parameter("map_frame", "camera_init")
        self.declare_parameter("robot_root_frame", "base_footprint")
        # body (FAST-LIO) ~= imu_link; imu_link is +0.2258 m above base_footprint in URDF.
        self.declare_parameter("imu_to_robot_root_xyz", [0.0, 0.0, -0.2258])
        self.declare_parameter("imu_to_robot_root_rpy", [0.0, 0.0, 0.0])

        odom_topic = str(self.get_parameter("odom_topic").value)
        self.map_frame = str(self.get_parameter("map_frame").value)
        self.robot_root_frame = str(self.get_parameter("robot_root_frame").value)
        self.imu_to_root_xyz = list(self.get_parameter("imu_to_robot_root_xyz").value)
        self.imu_to_root_rpy = list(self.get_parameter("imu_to_robot_root_rpy").value)

        self.tf_broadcaster = TransformBroadcaster(self)
        self.create_subscription(Odometry, odom_topic, self.odom_callback, 20)

        self.get_logger().info(
            "Bridging %s -> %s from %s (imu offset xyz=%s)"
            % (self.map_frame, self.robot_root_frame, odom_topic, self.imu_to_root_xyz)
        )

    def odom_callback(self, msg: Odometry) -> None:
        if msg.header.frame_id != self.map_frame:
            return

        root = TransformStamped()
        root.header.stamp = msg.header.stamp
        root.header.frame_id = self.map_frame
        root.child_frame_id = self.robot_root_frame
        root.transform.translation.x = (
            msg.pose.pose.position.x + self.imu_to_root_xyz[0]
        )
        root.transform.translation.y = (
            msg.pose.pose.position.y + self.imu_to_root_xyz[1]
        )
        root.transform.translation.z = (
            msg.pose.pose.position.z + self.imu_to_root_xyz[2]
        )
        root.transform.rotation = msg.pose.pose.orientation
        self.tf_broadcaster.sendTransform(root)


def main(args: Optional[list[str]] = None) -> None:
    rclpy.init(args=args)
    node = FastLioRobotTfBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

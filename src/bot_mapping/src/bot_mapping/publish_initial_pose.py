#!/usr/bin/env python3
"""Publish a one-shot /initialpose for FAST-LIO global localization."""

from __future__ import annotations

import sys
from typing import Optional

import rclpy
from geometry_msgs.msg import Point, Pose, PoseWithCovarianceStamped, Quaternion
from rclpy.node import Node

from bot_mapping.math3d import quaternion_from_euler


class PublishInitialPose(Node):
    def __init__(self) -> None:
        super().__init__("publish_initial_pose")
        self.publisher = self.create_publisher(PoseWithCovarianceStamped, "/initialpose", 10)

    def publish_pose(self, x: float, y: float, z: float, yaw: float, pitch: float, roll: float) -> None:
        quat = quaternion_from_euler(roll, pitch, yaw)
        msg = PoseWithCovarianceStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "map"
        msg.pose.pose = Pose(
            position=Point(x=x, y=y, z=z),
            orientation=Quaternion(x=quat[0], y=quat[1], z=quat[2], w=quat[3]),
        )
        self.publisher.publish(msg)
        self.get_logger().info("Published /initialpose: x=%.2f y=%.2f z=%.2f yaw=%.2f" % (x, y, z, yaw))


def main(args: Optional[list[str]] = None) -> None:
    rclpy.init(args=args)
    node = PublishInitialPose()

    if len(sys.argv) < 7:
        node.get_logger().error(
            "Usage: publish_initial_pose x y z yaw pitch roll"
        )
        rclpy.shutdown()
        return

    x, y, z, yaw, pitch, roll = (float(v) for v in sys.argv[1:7])
    node.publish_pose(x, y, z, yaw, pitch, roll)
    rclpy.spin_once(node, timeout_sec=0.5)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()

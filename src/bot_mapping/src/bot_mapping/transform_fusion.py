#!/usr/bin/env python3
"""Fuse FAST-LIO odometry with map_to_odom correction -> /localization + map TF."""

from __future__ import annotations

import copy
from typing import Optional

import numpy as np
import rclpy
from geometry_msgs.msg import Point, Pose, Quaternion, Transform, TransformStamped, Vector3
from nav_msgs.msg import Odometry
from rclpy.node import Node
from tf2_ros import TransformBroadcaster

from bot_mapping.math3d import matrix_to_quaternion, pose_to_matrix, translation_from_matrix


class TransformFusion(Node):
    def __init__(self) -> None:
        super().__init__("transform_fusion")

        self.cur_odom: Optional[Odometry] = None
        self.cur_map_to_odom: Optional[Odometry] = None

        self.tf_broadcaster = TransformBroadcaster(self)
        self.pub_localization = self.create_publisher(Odometry, "/localization", 10)

        self.create_subscription(Odometry, "/Odometry", self._odom_callback, 10)
        self.create_subscription(Odometry, "/map_to_odom", self._map_to_odom_callback, 10)
        self.create_timer(0.02, self._publish_fused_pose)

    def _odom_callback(self, msg: Odometry) -> None:
        self.cur_odom = msg

    def _map_to_odom_callback(self, msg: Odometry) -> None:
        self.cur_map_to_odom = msg

    def _publish_fused_pose(self) -> None:
        if self.cur_odom is None:
            return

        if self.cur_map_to_odom is not None:
            t_map_to_odom = pose_to_matrix(self.cur_map_to_odom.pose.pose)
        else:
            t_map_to_odom = np.eye(4)

        quat = matrix_to_quaternion(t_map_to_odom)
        tf_msg = TransformStamped()
        tf_msg.header.stamp = self.cur_odom.header.stamp
        tf_msg.header.frame_id = "map"
        tf_msg.child_frame_id = "camera_init"
        tf_msg.transform = Transform(
            translation=Vector3(
                x=float(t_map_to_odom[0, 3]),
                y=float(t_map_to_odom[1, 3]),
                z=float(t_map_to_odom[2, 3]),
            ),
            rotation=Quaternion(
                x=float(quat[0]), y=float(quat[1]), z=float(quat[2]), w=float(quat[3])
            ),
        )
        self.tf_broadcaster.sendTransform(tf_msg)

        odom = copy.copy(self.cur_odom)
        t_odom_to_body = pose_to_matrix(odom.pose.pose)
        t_map_to_body = t_map_to_odom @ t_odom_to_body
        xyz = translation_from_matrix(t_map_to_body)
        body_quat = matrix_to_quaternion(t_map_to_body)

        localization = Odometry()
        localization.header.stamp = odom.header.stamp
        localization.header.frame_id = "map"
        localization.child_frame_id = "body"
        localization.pose.pose = Pose(
            position=Point(x=float(xyz[0]), y=float(xyz[1]), z=float(xyz[2])),
            orientation=Quaternion(
                x=float(body_quat[0]), y=float(body_quat[1]),
                z=float(body_quat[2]), w=float(body_quat[3]),
            ),
        )
        localization.twist = odom.twist
        self.pub_localization.publish(localization)


def main(args: Optional[list[str]] = None) -> None:
    rclpy.init(args=args)
    node = TransformFusion()
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

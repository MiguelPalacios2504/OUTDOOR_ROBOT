#!/usr/bin/env python3
"""Scan-to-map ICP relocalization against a saved PCD (FAST-LIO localization pattern)."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Optional

import numpy as np
import open3d as o3d
import rclpy
from geometry_msgs.msg import Point, Pose, PoseWithCovarianceStamped, Quaternion
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Header

from bot_mapping.math3d import matrix_to_quaternion, pose_to_matrix
from bot_mapping.pointcloud_utils import pointcloud2_from_xyz, xyz_from_pointcloud2


class GlobalLocalization(Node):
    def __init__(self) -> None:
        super().__init__("global_localization")

        self.declare_parameter("pcd_map_path", "")
        self.declare_parameter("map_voxel_size", 0.4)
        self.declare_parameter("scan_voxel_size", 0.1)
        self.declare_parameter("freq_localization", 0.5)
        self.declare_parameter("localization_threshold", 0.8)
        self.declare_parameter("fov", 6.28319)
        self.declare_parameter("fov_far", 30.0)

        map_path = str(self.get_parameter("pcd_map_path").value)
        if not map_path or not Path(map_path).is_file():
            raise RuntimeError("pcd_map_path must point to an existing .pcd file")

        self.map_voxel_size = float(self.get_parameter("map_voxel_size").value)
        self.scan_voxel_size = float(self.get_parameter("scan_voxel_size").value)
        self.localization_threshold = float(self.get_parameter("localization_threshold").value)
        self.fov = float(self.get_parameter("fov").value)
        self.fov_far = float(self.get_parameter("fov_far").value)

        self.global_map = self._load_map(map_path)
        self.t_map_to_odom = np.eye(4)
        self.cur_odom: Optional[Odometry] = None
        self.cur_scan: Optional[o3d.geometry.PointCloud] = None
        self.initialized = False

        self.pub_pc_in_map = self.create_publisher(PointCloud2, "/cur_scan_in_map", 10)
        self.pub_submap = self.create_publisher(PointCloud2, "/submap", 10)
        self.pub_map_to_odom = self.create_publisher(Odometry, "/map_to_odom", 10)

        self.create_subscription(PointCloud2, "/cloud_registered", self._scan_callback, 10)
        self.create_subscription(Odometry, "/Odometry", self._odom_callback, 10)
        self.create_subscription(
            PoseWithCovarianceStamped, "/initialpose", self._initial_pose_callback, 10
        )

        freq = float(self.get_parameter("freq_localization").value)
        self.create_timer(1.0 / max(freq, 0.05), self._localization_timer)

        self.get_logger().info("Loaded map %s (%d points after voxel %.2f m)" % (
            map_path, len(self.global_map.points), self.map_voxel_size
        ))

    def _load_map(self, map_path: str) -> o3d.geometry.PointCloud:
        cloud = o3d.io.read_point_cloud(map_path)
        if cloud.is_empty():
            raise RuntimeError("PCD is empty: %s" % map_path)
        return self._voxel_down_sample(cloud, self.map_voxel_size)

    def _voxel_down_sample(self, cloud: o3d.geometry.PointCloud, voxel_size: float):
        try:
            return cloud.voxel_down_sample(voxel_size)
        except AttributeError:
            return o3d.geometry.voxel_down_sample(cloud, voxel_size)

    def _registration_at_scale(
        self, scan: o3d.geometry.PointCloud, submap: o3d.geometry.PointCloud,
        initial: np.ndarray, scale: float,
    ) -> tuple[np.ndarray, float]:
        result = o3d.pipelines.registration.registration_icp(
            self._voxel_down_sample(scan, self.scan_voxel_size * scale),
            self._voxel_down_sample(submap, self.map_voxel_size * scale),
            1.0 * scale,
            initial,
            o3d.pipelines.registration.TransformationEstimationPointToPoint(),
            o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=20),
        )
        return result.transformation, result.fitness

    @staticmethod
    def _inverse_se3(trans: np.ndarray) -> np.ndarray:
        inv = np.eye(4)
        inv[:3, :3] = trans[:3, :3].T
        inv[:3, 3] = -trans[:3, :3].T @ trans[:3, 3]
        return inv

    def _publish_point_cloud(self, publisher, header: Header, points: np.ndarray) -> None:
        publisher.publish(pointcloud2_from_xyz(header, points[:, :3]))

    def _crop_map_fov(self, pose_estimation: np.ndarray) -> o3d.geometry.PointCloud:
        t_odom_to_body = pose_to_matrix(self.cur_odom.pose.pose)
        t_map_to_body = pose_estimation @ t_odom_to_body
        t_body_to_map = self._inverse_se3(t_map_to_body)

        map_points = np.asarray(self.global_map.points)
        homog = np.column_stack([map_points, np.ones(len(map_points))])
        points_in_body = (t_body_to_map @ homog.T).T

        if self.fov > 3.14:
            mask = (
                (points_in_body[:, 0] < self.fov_far)
                & (np.abs(np.arctan2(points_in_body[:, 1], points_in_body[:, 0])) < self.fov / 2.0)
            )
        else:
            mask = (
                (points_in_body[:, 0] > 0)
                & (points_in_body[:, 0] < self.fov_far)
                & (np.abs(np.arctan2(points_in_body[:, 1], points_in_body[:, 0])) < self.fov / 2.0)
            )

        submap = o3d.geometry.PointCloud()
        submap.points = o3d.utility.Vector3dVector(map_points[mask])

        header = self.cur_odom.header
        header.frame_id = "map"
        self._publish_point_cloud(self.pub_submap, header, map_points[mask][::10])
        return submap

    def _publish_map_to_odom(self, transform: np.ndarray) -> None:
        msg = Odometry()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "map"
        xyz = transform[:3, 3]
        quat = matrix_to_quaternion(transform)
        msg.pose.pose = Pose(
            position=Point(x=float(xyz[0]), y=float(xyz[1]), z=float(xyz[2])),
            orientation=Quaternion(
                x=float(quat[0]), y=float(quat[1]), z=float(quat[2]), w=float(quat[3])
            ),
        )
        self.pub_map_to_odom.publish(msg)

    def _global_localization(self, pose_estimation: np.ndarray) -> bool:
        if self.cur_scan is None or self.cur_odom is None:
            return False

        scan = copy.copy(self.cur_scan)
        submap = self._crop_map_fov(pose_estimation)
        if len(submap.points) < 50:
            self.get_logger().warn("Submap too small for ICP")
            return False

        transform, _ = self._registration_at_scale(scan, submap, pose_estimation, scale=5.0)
        transform, fitness = self._registration_at_scale(scan, submap, transform, scale=1.0)

        if fitness > self.localization_threshold:
            self.t_map_to_odom = transform
            self._publish_map_to_odom(transform)
            self.get_logger().info("Localization OK (fitness=%.3f)" % fitness)
            return True

        self.get_logger().warn("ICP failed (fitness=%.3f < %.3f)" % (
            fitness, self.localization_threshold
        ))
        return False

    def _odom_callback(self, msg: Odometry) -> None:
        self.cur_odom = msg

    def _scan_callback(self, msg: PointCloud2) -> None:
        xyz = xyz_from_pointcloud2(msg)
        scan = o3d.geometry.PointCloud()
        scan.points = o3d.utility.Vector3dVector(xyz)
        self.cur_scan = scan
        self._publish_point_cloud(self.pub_pc_in_map, msg.header, xyz)

    def _initial_pose_callback(self, msg: PoseWithCovarianceStamped) -> None:
        initial = pose_to_matrix(msg.pose.pose)
        self.initialized = True
        self.get_logger().info("Initial pose received in map frame")
        if self.cur_scan is not None:
            self._global_localization(initial)

    def _localization_timer(self) -> None:
        if not self.initialized:
            self.get_logger().info("Waiting for /initialpose (RViz 2D Pose Estimate)...", throttle_duration_sec=5.0)
            return
        if self.cur_scan is not None:
            self._global_localization(self.t_map_to_odom)


def main(args: Optional[list[str]] = None) -> None:
    rclpy.init(args=args)
    node = GlobalLocalization()
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

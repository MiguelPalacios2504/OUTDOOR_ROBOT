#!/usr/bin/env python3
"""Add Velodyne ring/time fields to Gazebo PointCloud2 for LIO-SAM."""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2, PointField
from sensor_msgs_py import point_cloud2


class VelodyneCloudAdapter(Node):
    def __init__(self) -> None:
        super().__init__("velodyne_cloud_adapter")

        self.declare_parameter("input_topic", "/lidar/points")
        self.declare_parameter("output_topic", "/lio_sam/points")
        self.declare_parameter("n_scan", 39)
        self.declare_parameter("vertical_min_deg", -8.0)
        self.declare_parameter("vertical_max_deg", 90.0)

        input_topic = str(self.get_parameter("input_topic").value)
        output_topic = str(self.get_parameter("output_topic").value)
        self.n_scan = int(self.get_parameter("n_scan").value)
        self.vertical_min = math.radians(float(self.get_parameter("vertical_min_deg").value))
        self.vertical_max = math.radians(float(self.get_parameter("vertical_max_deg").value))

        self.publisher = self.create_publisher(PointCloud2, output_topic, qos_profile_sensor_data)
        self.subscription = self.create_subscription(
            PointCloud2,
            input_topic,
            self.cloud_callback,
            qos_profile_sensor_data,
        )

        self.get_logger().info(
            "Velodyne adapter %s -> %s (N_SCAN=%d, elevation %.1f..%.1f deg)"
            % (
                input_topic,
                output_topic,
                self.n_scan,
                math.degrees(self.vertical_min),
                math.degrees(self.vertical_max),
            )
        )

    def _elevation_rad(self, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
        horizontal = np.hypot(x, y)
        return np.arctan2(z, np.maximum(horizontal, 1e-6))

    def _ring_index(self, elevation: np.ndarray) -> np.ndarray:
        span = self.vertical_max - self.vertical_min
        if span < 1e-6:
            return np.zeros_like(elevation, dtype=np.uint16)
        normalized = (elevation - self.vertical_min) / span
        rings = np.clip(
            np.round(normalized * (self.n_scan - 1)).astype(np.int32),
            0,
            self.n_scan - 1,
        )
        return rings.astype(np.uint16)

    def cloud_callback(self, msg: PointCloud2) -> None:
        points = list(point_cloud2.read_points(msg, field_names=("x", "y", "z"), skip_nans=True))
        if not points:
            return

        xyz = np.asarray(points, dtype=np.float32)
        x, y, z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
        elevation = self._elevation_rad(x, y, z)
        rings = self._ring_index(elevation)

        fields = [
            PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1),
            PointField(name="intensity", offset=12, datatype=PointField.FLOAT32, count=1),
            PointField(name="ring", offset=16, datatype=PointField.UINT16, count=1),
            PointField(name="time", offset=18, datatype=PointField.FLOAT32, count=1),
        ]

        points_out = [
            (
                float(x[i]),
                float(y[i]),
                float(z[i]),
                0.0,
                int(rings[i]),
                0.0,
            )
            for i in range(len(x))
        ]
        out = point_cloud2.create_cloud(msg.header, fields, points_out)
        self.publisher.publish(out)


def main(args: Optional[list[str]] = None) -> None:
    rclpy.init(args=args)
    node = VelodyneCloudAdapter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

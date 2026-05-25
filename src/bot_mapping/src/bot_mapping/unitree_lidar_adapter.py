#!/usr/bin/env python3
"""Add Velodyne ring/time fields to Unitree L2 PointCloud2 for FAST-LIO."""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2, PointField
from sensor_msgs_py import point_cloud2

# PCL velodyne_ros::Point (EIGEN_ALIGN16): x,y,z, pad, intensity, time, ring + tail padding = 32 B
_VELODYNE_DTYPE = np.dtype(
    [
        ("x", "<f4"),
        ("y", "<f4"),
        ("z", "<f4"),
        ("padding", "<f4"),
        ("intensity", "<f4"),
        ("time", "<f4"),
        ("ring", "<u2"),
        ("_align", "V6", 1),
    ]
)
assert _VELODYNE_DTYPE.itemsize == 32

_VELODYNE_FIELDS = [
    PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1),
    PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1),
    PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1),
    PointField(name="padding", offset=12, datatype=PointField.FLOAT32, count=1),
    PointField(name="intensity", offset=16, datatype=PointField.FLOAT32, count=1),
    PointField(name="time", offset=20, datatype=PointField.FLOAT32, count=1),
    PointField(name="ring", offset=24, datatype=PointField.UINT16, count=1),
]


class UnitreeLidarAdapter(Node):
    def __init__(self) -> None:
        super().__init__("unitree_lidar_adapter")

        self.declare_parameter("input_topic", "/lidar/points")
        self.declare_parameter("output_topic", "/fast_lio/points")
        self.declare_parameter("n_scan", 39)
        self.declare_parameter("vertical_min_deg", -8.0)
        self.declare_parameter("vertical_max_deg", 90.0)
        self.declare_parameter("scan_rate_hz", 5.55)

        input_topic = str(self.get_parameter("input_topic").value)
        output_topic = str(self.get_parameter("output_topic").value)
        self.n_scan = int(self.get_parameter("n_scan").value)
        self.vertical_min = math.radians(float(self.get_parameter("vertical_min_deg").value))
        self.vertical_max = math.radians(float(self.get_parameter("vertical_max_deg").value))
        self.scan_period = 1.0 / float(self.get_parameter("scan_rate_hz").value)

        self.publisher = self.create_publisher(PointCloud2, output_topic, qos_profile_sensor_data)
        self.subscription = self.create_subscription(
            PointCloud2,
            input_topic,
            self.cloud_callback,
            qos_profile_sensor_data,
        )

        self.get_logger().info(
            "Unitree adapter %s -> %s (N_SCAN=%d, scan %.2f Hz)"
            % (input_topic, output_topic, self.n_scan, 1.0 / self.scan_period)
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

    def _time_offset_sec(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Per-point offset within the scan period from horizontal angle."""
        yaw = np.arctan2(y, x)
        normalized = (yaw + math.pi) / (2.0 * math.pi)
        return normalized * self.scan_period

    @staticmethod
    def _xyz_arrays(points: list) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
        """Extract x,y,z from read_points (structured or tuple rows)."""
        if not points:
            return None
        structured = np.asarray(points)
        if structured.dtype.names and "x" in structured.dtype.names:
            x = np.asarray(structured["x"], dtype=np.float32)
            y = np.asarray(structured["y"], dtype=np.float32)
            z = np.asarray(structured["z"], dtype=np.float32)
        else:
            arr = np.asarray(points, dtype=np.float32)
            if arr.ndim != 2 or arr.shape[1] < 3:
                return None
            x, y, z = arr[:, 0], arr[:, 1], arr[:, 2]
        return x, y, z

    def _pack_velodyne_cloud(
        self,
        header,
        x: np.ndarray,
        y: np.ndarray,
        z: np.ndarray,
        rings: np.ndarray,
        times: np.ndarray,
    ) -> PointCloud2:
        n = x.shape[0]
        cloud = np.zeros(n, dtype=_VELODYNE_DTYPE)
        cloud["x"] = x
        cloud["y"] = y
        cloud["z"] = z
        cloud["intensity"] = 0.0
        cloud["time"] = times
        cloud["ring"] = rings

        msg = PointCloud2()
        msg.header = header
        msg.height = 1
        msg.width = n
        msg.fields = _VELODYNE_FIELDS
        msg.is_bigendian = False
        msg.point_step = _VELODYNE_DTYPE.itemsize
        msg.row_step = msg.point_step * n
        msg.is_dense = True
        msg.data = cloud.tobytes()
        return msg

    def cloud_callback(self, msg: PointCloud2) -> None:
        points = list(point_cloud2.read_points(msg, field_names=("x", "y", "z"), skip_nans=True))
        xyz = self._xyz_arrays(points)
        if xyz is None:
            return
        x, y, z = xyz
        elevation = self._elevation_rad(x, y, z)
        rings = self._ring_index(elevation)
        times = self._time_offset_sec(x, y)
        self.publisher.publish(self._pack_velodyne_cloud(msg.header, x, y, z, rings, times))


def main(args: Optional[list[str]] = None) -> None:
    rclpy.init(args=args)
    node = UnitreeLidarAdapter()
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

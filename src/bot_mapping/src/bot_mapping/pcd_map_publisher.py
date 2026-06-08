#!/usr/bin/env python3
"""Publish a saved PCD as PointCloud2 for RViz (display only, does not modify the file)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import open3d as o3d
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Header

from bot_mapping.pointcloud_utils import pointcloud2_from_xyz


class PcdMapPublisher(Node):
    def __init__(self) -> None:
        super().__init__("pcd_map_publisher")

        self.declare_parameter("pcd_map_path", "")
        self.declare_parameter("map_topic", "/map")
        self.declare_parameter("map_frame", "map")
        self.declare_parameter("publish_hz", 0.5)
        self.declare_parameter("viz_voxel_size", 0.0)

        map_path = str(self.get_parameter("pcd_map_path").value)
        if not map_path or not Path(map_path).is_file():
            raise RuntimeError("pcd_map_path must point to an existing .pcd file")

        self.map_frame = str(self.get_parameter("map_frame").value)
        cloud = o3d.io.read_point_cloud(map_path)
        if cloud.is_empty():
            raise RuntimeError("PCD is empty: %s" % map_path)

        viz_voxel = float(self.get_parameter("viz_voxel_size").value)
        if viz_voxel > 0.0:
            try:
                cloud = cloud.voxel_down_sample(viz_voxel)
            except AttributeError:
                cloud = o3d.geometry.voxel_down_sample(cloud, viz_voxel)

        self.points = np.asarray(cloud.points, dtype=np.float32)
        topic = str(self.get_parameter("map_topic").value)
        self.publisher = self.create_publisher(PointCloud2, topic, 10)

        hz = max(float(self.get_parameter("publish_hz").value), 0.1)
        self.create_timer(1.0 / hz, self._publish_map)

        self.get_logger().info(
            "Publishing %s (%d points) on %s" % (map_path, len(self.points), topic)
        )

    def _publish_map(self) -> None:
        header = Header()
        header.stamp = self.get_clock().now().to_msg()
        header.frame_id = self.map_frame
        self.publisher.publish(pointcloud2_from_xyz(header, self.points))


def main(args: Optional[list[str]] = None) -> None:
    rclpy.init(args=args)
    node = PcdMapPublisher()
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

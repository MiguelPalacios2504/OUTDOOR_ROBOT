"""PointCloud2 helpers without ros2_numpy."""

from __future__ import annotations

import numpy as np
from sensor_msgs.msg import PointCloud2, PointField
from sensor_msgs_py import point_cloud2


def xyz_from_pointcloud2(msg: PointCloud2) -> np.ndarray:
    points = list(point_cloud2.read_points(msg, field_names=("x", "y", "z"), skip_nans=True))
    if not points:
        return np.zeros((0, 3), dtype=np.float32)
    arr = np.asarray(points)
    if arr.dtype.names and "x" in arr.dtype.names:
        return np.column_stack(
            [arr["x"], arr["y"], arr["z"]]
        ).astype(np.float32)
    return np.asarray(points, dtype=np.float32)[:, :3]


def pointcloud2_from_xyz(header, xyz: np.ndarray) -> PointCloud2:
    fields = [
        PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1),
        PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1),
        PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1),
    ]
    return point_cloud2.create_cloud(header, fields, xyz.tolist())

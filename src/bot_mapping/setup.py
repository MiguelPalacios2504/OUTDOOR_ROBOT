from setuptools import find_packages, setup

package_name = "bot_mapping"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(where="src", exclude=["test"]),
    package_dir={"": "src"},
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (
            f"share/{package_name}/config",
            [
                "config/fast_lio_unitree_l2.yaml",
                "config/fast_lio_unitree_l2_direct.yaml",
                "config/fast_lio_unitree_l2_sim.yaml",
                "config/fast_lio_localization.yaml",
            ],
        ),
        (
            f"share/{package_name}/launch",
            ["launch/fast_lio.launch.py", "launch/fast_lio_localization.launch.py"],
        ),
        (
            f"share/{package_name}/rviz",
            ["rviz/mapping_fast_lio.rviz", "rviz/localization_fast_lio.rviz"],
        ),
        (f"share/{package_name}/repos", ["repos/fast_lio.repos"]),
        (f"share/{package_name}/patches", ["patches/fast_lio_jazzy.patch"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="aditya",
    maintainer_email="kotteaditya919@gmail.com",
    description="FAST-LIO2 mapping bringup for the outdoor bot (3D lidar + IMU).",
    license="TODO: License declaration",
    entry_points={
        "console_scripts": [
            "unitree_lidar_adapter = bot_mapping.unitree_lidar_adapter:main",
            "fast_lio_robot_tf_bridge = bot_mapping.fast_lio_robot_tf_bridge:main",
            "global_localization = bot_mapping.global_localization:main",
            "transform_fusion = bot_mapping.transform_fusion:main",
            "pcd_map_publisher = bot_mapping.pcd_map_publisher:main",
            "publish_initial_pose = bot_mapping.publish_initial_pose:main",
        ],
    },
)

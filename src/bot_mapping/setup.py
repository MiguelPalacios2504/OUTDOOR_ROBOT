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
        (f"share/{package_name}/config", ["config/lio_sam_params.yaml"]),
        (f"share/{package_name}/launch", [
            "launch/lio_sam.launch.py",
            "launch/mapping_sim.launch.py",
        ]),
        (f"share/{package_name}/rviz", ["rviz/mapping_lio_sam.rviz"]),
        (f"share/{package_name}/repos", ["repos/lio_sam.repos"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="aditya",
    maintainer_email="kotteaditya919@gmail.com",
    description="LIO-SAM mapping bringup for the outdoor bot (3D lidar + IMU).",
    license="TODO: License declaration",
    entry_points={
        "console_scripts": [
            "velodyne_cloud_adapter = bot_mapping.velodyne_cloud_adapter:main",
        ],
    },
)

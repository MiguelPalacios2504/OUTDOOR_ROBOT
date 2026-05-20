from setuptools import find_packages, setup


package_name = "robby_control"


setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(where="src", exclude=["test"]),
    package_dir={"": "src"},
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/config", ["config/joint_command_bridge.yaml"]),
        (f"share/{package_name}/config", ["config/swerve_cmd.yaml"]),
        (f"share/{package_name}/launch", ["launch/swerve.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="aditya",
    maintainer_email="kotteaditya919@gmail.com",
    description="Control and odometry nodes for the ITQ Robby platform.",
    license="TODO: License declaration",
    entry_points={
        "console_scripts": [
            "joint_command_bridge = robby_control.joint_command_bridge:main",
            "swerve_cmd_node = robby_control.swerve_cmd_node:main",
        ],
    },
)

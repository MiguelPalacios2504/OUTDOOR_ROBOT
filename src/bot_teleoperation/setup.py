from setuptools import find_packages, setup


package_name = "bot_teleoperation"


setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(where="src", exclude=["test"]),
    package_dir={"": "src"},
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/config", ["config/teleop.yaml"]),
        (f"share/{package_name}/launch", ["launch/teleop.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="aditya",
    maintainer_email="kotteaditya919@gmail.com",
    description="Keyboard teleoperation interface for the outdoor bot platform.",
    license="TODO: License declaration",
    entry_points={
        "console_scripts": [
            "keyboard_teleop_node = bot_teleoperation.keyboard_teleop_node:main",
        ],
    },
)

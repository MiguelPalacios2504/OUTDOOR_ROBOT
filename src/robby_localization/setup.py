from setuptools import find_packages, setup


package_name = "robby_localization"


setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(where="src", exclude=["test"]),
    package_dir={"": "src"},
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/config", ["config/localization.yaml", "config/nav2.yaml"]),
        (
            f"share/{package_name}/launch",
            [
                "launch/localization.launch.py",
                "launch/nav2.launch.py",
                "launch/localization_rviz.launch.py",
            ],
        ),
        (f"share/{package_name}/rviz", ["rviz/localization.rviz"]),
        (
            f"share/{package_name}/maps",
            [
                "../../maps/arena_map.yaml",
                "../../maps/arena_map.pgm",
            ],
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="aditya",
    maintainer_email="kotteaditya919@gmail.com",
    description="Localization and sensor fusion nodes for the ITQ Robby platform.",
    license="TODO: License declaration",
    entry_points={
        "console_scripts": [
            "localization_input_node = robby_localization.localization_input_node:main",
        ],
    },
)

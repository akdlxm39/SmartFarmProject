from setuptools import find_packages, setup

package_name = 'conveyor_vision_test'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ssafy',
    maintainer_email='hermes@example.com',
    description='SmartFarmProject conveyor top-view ROI red/green object detection test node.',
    license='MIT',
    extras_require={
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': [
            'topview_color_detector = conveyor_vision_test.topview_color_detector:main',
            'conveyor_modbus_command = conveyor_vision_test.conveyor_modbus_command:main',
        ],
    },
)

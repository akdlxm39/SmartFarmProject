from setuptools import setup

package_name = 'slam_pjt'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='SSAFY',
    maintainer_email='ssafy@example.com',
    description='SmartFarmProject TurtleBot SLAM/Navigation helper package.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'turtlebot_modbus_heartbeat = slam_pjt.turtlebot_modbus_heartbeat:main',
        ],
    },
)

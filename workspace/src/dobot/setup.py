from glob import glob

from setuptools import find_packages, setup

package_name = 'dobot'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('config/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ssafy',
    maintainer_email='hermes@example.com',
    description='SmartFarmProject Dobot Magician ROS2 harvest, calibration, and vision-trigger control package.',
    license='MIT',
    extras_require={'test': ['pytest']},
    entry_points={
        'console_scripts': [
            'calibrate_positions = dobot.calibrate_positions:main',
            'calibrate_harvest_positions = dobot.calibrate_harvest_positions:main',
            'harvest_test = dobot.harvest_test:main',
        ],
    },
)

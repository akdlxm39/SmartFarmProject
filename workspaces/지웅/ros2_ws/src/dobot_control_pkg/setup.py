from glob import glob

from setuptools import find_packages, setup

package_name = 'dobot_control_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('config/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ssafy',
    maintainer_email='hermes@example.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'calibrate_positions = dobot_control_pkg.calibrate_positions:main',
            'calibrate_harvest_positions = dobot_control_pkg.calibrate_harvest_positions:main',
            'harvest_test = dobot_control_pkg.harvest_test:main',
        ],
    },
)

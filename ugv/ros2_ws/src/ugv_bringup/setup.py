import os
from glob import glob
from setuptools import setup

package_name = 'ugv_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        # ament package index marker
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        # package manifest
        ('share/' + package_name, ['package.xml']),
        # launch files
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.py')),
        # config files
        (os.path.join('share', package_name, 'config'),
            glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='UAV-UGV Land Survey Team',
    maintainer_email='todo@example.com',
    description='Launch files and configuration for UGV VSLAM and autonomous navigation.',
    license='Apache-2.0',
    entry_points={},
)

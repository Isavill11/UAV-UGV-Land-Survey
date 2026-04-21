from setuptools import setup

package_name = 'ugv_ackermann'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    py_modules=[],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='you@example.com',
    description='ROS2 ackermann converter node',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'ackermann_converter = ugv_ackermann.ackermann_converter_node:main',
        ],
    },
)

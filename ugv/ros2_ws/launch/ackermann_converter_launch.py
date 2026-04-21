from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='ugv_ackermann',
            executable='ackermann_converter',
            name='ackermann_converter',
            output='screen',
            parameters=[
                {'wheel_base': 0.45},
                {'max_steer_angle': 0.6},
                {'max_speed': 1.0},
            ],
        )
    ])

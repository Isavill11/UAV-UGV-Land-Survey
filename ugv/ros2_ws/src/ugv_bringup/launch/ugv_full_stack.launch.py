# ugv_full_stack.launch.py
#
# Single entry-point for the complete UGV autonomous survey stack:
#
#   1. Static TF  – base_link -> camera_link (physical camera mounting)
#   2. VSLAM      – RealSense + RTAB-Map (mapping or localisation)
#   3. Nav2       – path planning, control, recovery, waypoint following
#
# Adjust the camera_tf arguments below to match your physical camera position
# before running on the robot.  See config/frames.yaml for documentation.
#
# Usage:
#   ros2 launch ugv_bringup ugv_full_stack.launch.py
#
#   # Localise using an existing map (skip mapping):
#   ros2 launch ugv_bringup ugv_full_stack.launch.py localization:=true
#
#   # Verbose Nav2 logging:
#   ros2 launch ugv_bringup ugv_full_stack.launch.py log_level:=debug

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    pkg_dir = get_package_share_directory('ugv_bringup')

    # ── Launch arguments ──────────────────────────────────────────────────
    localization_arg = DeclareLaunchArgument(
        'localization',
        default_value='false',
        description='true = RTAB-Map localisation only (requires existing ~/.ros/rtabmap.db).',
    )
    log_level_arg = DeclareLaunchArgument(
        'log_level',
        default_value='info',
        description='Logging level for Nav2 nodes.',
    )

    # ── 1. Static TF: base_link -> camera_link ────────────────────────────
    # static_transform_publisher args: x y z yaw pitch roll parent child
    #
    # Current values (metres / radians):
    #   x=0.15  – camera 15 cm forward of base_link origin
    #   y=0.00  – centred left-right
    #   z=0.25  – 25 cm above base_link
    #   yaw=pitch=roll=0 – level, forward-facing
    #
    # Edit config/frames.yaml for documentation; edit the arguments list
    # below to apply changes.
    camera_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='camera_tf_publisher',
        arguments=[
            '0.15', '0.0', '0.25',   # x  y  z  (metres)
            '0.0',  '0.0', '0.0',    # yaw  pitch  roll  (radians)
            'base_link', 'camera_link',
        ],
        output='screen',
    )

    # ── 2. VSLAM ─────────────────────────────────────────────────────────
    vslam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_dir, 'launch', 'ugv_vslam.launch.py')
        ),
        launch_arguments={
            'localization': LaunchConfiguration('localization'),
        }.items(),
    )

    # ── 3. Nav2 ───────────────────────────────────────────────────────────
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_dir, 'launch', 'ugv_nav2.launch.py')
        ),
        launch_arguments={
            'log_level': LaunchConfiguration('log_level'),
        }.items(),
    )

    return LaunchDescription([
        localization_arg,
        log_level_arg,
        # Static TF must be up before VSLAM and Nav2 nodes try to look up frames.
        camera_tf,
        vslam,
        nav2,
    ])

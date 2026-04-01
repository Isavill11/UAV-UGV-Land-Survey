# ugv_vslam.launch.py
#
# Full UGV RGB-D VSLAM bring-up using RTAB-Map on ROS 2 Jazzy.
#
# Hardware  : Intel RealSense D4xx series (depth aligned in driver)
# Pipeline  : realsense2_camera -> rgbd_sync -> rgbd_odometry -> rtabmap
# TF tree   : map -> odom -> base_link  (published by RTAB-Map nodes)
#
# Usage:
#   ros2 launch ugv_bringup ugv_vslam.launch.py
#   ros2 launch ugv_bringup ugv_vslam.launch.py localization:=true
#   ros2 launch ugv_bringup ugv_vslam.launch.py rtabmap_viz:=true

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetParameter


# ---------------------------------------------------------------------------
# Topic names published by realsense2_camera with default namespace/name.
# Both camera_namespace and camera_name default to "camera", so all topics
# are under /camera/camera/...
# ---------------------------------------------------------------------------
COLOR_TOPIC      = "/camera/camera/color/image_raw"
COLOR_INFO_TOPIC = "/camera/camera/color/camera_info"
DEPTH_TOPIC      = "/camera/camera/aligned_depth_to_color/image_raw"


def generate_launch_description():

    pkg_dir = get_package_share_directory('ugv_bringup')
    rtabmap_params = os.path.join(pkg_dir, 'config', 'rtabmap_params.yaml')

    realsense_launch_dir = os.path.join(
        get_package_share_directory('realsense2_camera'), 'launch'
    )

    # ------------------------------------------------------------------
    # Launch arguments
    # ------------------------------------------------------------------
    localization_arg = DeclareLaunchArgument(
        'localization',
        default_value='false',
        description='true = localisation only (no new map nodes created).',
    )
    rtabmap_viz_arg = DeclareLaunchArgument(
        'rtabmap_viz',
        default_value='false',
        description='true = launch RTAB-Map built-in visualiser.',
    )

    # ------------------------------------------------------------------
    # Shared parameters loaded from YAML + inline overrides
    # ------------------------------------------------------------------
    # QoS 2 = sensor_data (Best Effort) – matches realsense2_camera defaults.
    shared_params = [
        rtabmap_params,
        {
            'qos':             2,
            'approx_sync':     True,
            'subscribe_depth': True,
            'frame_id':        'base_link',
            'odom_frame_id':   'odom',
            'map_frame_id':    'map',
            'publish_tf':      True,
        },
    ]

    rgbd_remappings = [
        ('rgb/image',       COLOR_TOPIC),
        ('rgb/camera_info', COLOR_INFO_TOPIC),
        ('depth/image',     DEPTH_TOPIC),
    ]

    # ------------------------------------------------------------------
    # 1. RealSense camera driver
    # ------------------------------------------------------------------
    realsense_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(realsense_launch_dir, 'rs_launch.py')
        ),
        launch_arguments={
            'align_depth.enable':          'true',
            'depth_module.emitter_enabled': '1',
            'rgb_camera.profile':          '640x360x30',
            'enable_sync':                 'true',
        }.items(),
    )

    # ------------------------------------------------------------------
    # 2. RGB-D Sync  (synchronises colour + depth streams)
    # ------------------------------------------------------------------
    rgbd_sync_node = Node(
        package='rtabmap_sync',
        executable='rgbd_sync',
        name='rgbd_sync',
        output='screen',
        parameters=shared_params,
        remappings=rgbd_remappings,
    )

    # ------------------------------------------------------------------
    # 3. RGB-D Odometry  (visual odometry -> /rtabmap/odom)
    # ------------------------------------------------------------------
    rgbd_odom_node = Node(
        package='rtabmap_odom',
        executable='rgbd_odometry',
        name='rgbd_odometry',
        output='screen',
        parameters=shared_params,
        remappings=rgbd_remappings,
    )

    # ------------------------------------------------------------------
    # 4a. RTAB-Map SLAM  (mapping mode – default)
    # ------------------------------------------------------------------
    rtabmap_slam_node = Node(
        condition=UnlessCondition(LaunchConfiguration('localization')),
        package='rtabmap_slam',
        executable='rtabmap',
        name='rtabmap',
        output='screen',
        parameters=shared_params,
        remappings=rgbd_remappings,
        arguments=['-d'],   # delete previous DB so each run starts fresh
    )

    # ------------------------------------------------------------------
    # 4b. RTAB-Map SLAM  (localisation only – no new map nodes)
    # ------------------------------------------------------------------
    rtabmap_loc_node = Node(
        condition=IfCondition(LaunchConfiguration('localization')),
        package='rtabmap_slam',
        executable='rtabmap',
        name='rtabmap',
        output='screen',
        parameters=[
            *shared_params,
            {
                'Mem/IncrementalMemory':  'false',
                'Mem/InitWMWithAllNodes': 'true',
            },
        ],
        remappings=rgbd_remappings,
    )

    # ------------------------------------------------------------------
    # 5. RTAB-Map visualiser  (optional, off by default)
    # ------------------------------------------------------------------
    rtabmap_viz_node = Node(
        condition=IfCondition(LaunchConfiguration('rtabmap_viz')),
        package='rtabmap_viz',
        executable='rtabmap_viz',
        name='rtabmap_viz',
        output='screen',
        parameters=shared_params,
        remappings=rgbd_remappings,
    )

    return LaunchDescription([
        localization_arg,
        rtabmap_viz_arg,
        SetParameter(name='use_sim_time', value=False),
        # Launch order matters: camera -> sync -> odom -> slam
        realsense_node,
        rgbd_sync_node,
        rgbd_odom_node,
        rtabmap_slam_node,
        rtabmap_loc_node,
        rtabmap_viz_node,
    ])

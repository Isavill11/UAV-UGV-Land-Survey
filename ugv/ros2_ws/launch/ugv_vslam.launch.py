# ugv_vslam.launch.py
#
# Full UGV RGB-D VSLAM bring-up using RTAB-Map on ROS 2 Jazzy.
#
# Hardware  : Intel RealSense D4xx series (depth aligned in driver)
# Middleware: realsense2_camera  → rtabmap_sync → rtabmap_odom → rtabmap_slam
# TF tree   : map → odom → base_link
#
# Usage:
#   ros2 launch ugv_vslam ugv_vslam.launch.py
#   ros2 launch ugv_vslam ugv_vslam.launch.py localization:=true  # localise only
#   ros2 launch ugv_vslam ugv_vslam.launch.py rtabmap_viz:=true   # open RTAB-Map GUI

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetParameter


# ---------------------------------------------------------------------------
# Topic names published by realsense2_camera with default namespace/name.
# The driver uses camera_namespace/camera_name, both default to "camera",
# so all topics are under /camera/camera/...
# ---------------------------------------------------------------------------
COLOR_TOPIC       = "/camera/camera/color/image_raw"
COLOR_INFO_TOPIC  = "/camera/camera/color/camera_info"
DEPTH_TOPIC       = "/camera/camera/aligned_depth_to_color/image_raw"


def generate_launch_description():

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------
    # Config file is in ../config/ relative to this launch file.
    _this_dir   = os.path.dirname(os.path.abspath(__file__))
    _config_dir = os.path.join(_this_dir, "..", "config")
    rtabmap_params = os.path.join(_config_dir, "rtabmap_params.yaml")

    # realsense2_camera launch file (installed by ros-jazzy-realsense2-camera)
    realsense_launch_dir = os.path.join(
        get_package_share_directory("realsense2_camera"), "launch"
    )

    # ------------------------------------------------------------------
    # Launch arguments
    # ------------------------------------------------------------------
    localization_arg = DeclareLaunchArgument(
        "localization",
        default_value="false",
        description="true = localisation only (no new map nodes created).",
    )
    rtabmap_viz_arg = DeclareLaunchArgument(
        "rtabmap_viz",
        default_value="false",
        description="true = launch RTAB-Map's built-in visualiser.",
    )
    delete_db_arg = DeclareLaunchArgument(
        "delete_db_on_start",
        default_value="true",
        description="Delete rtabmap.db on start so every run begins fresh.",
    )

    # ------------------------------------------------------------------
    # Shared parameters loaded from YAML + inline overrides
    # ------------------------------------------------------------------
    # QoS 2 = sensor_data (Best Effort) – matches realsense2_camera defaults.
    shared_params = [
        rtabmap_params,
        {
            "qos":            2,
            "approx_sync":    True,
            "subscribe_depth": True,
            "frame_id":       "base_link",
            "odom_frame_id":  "odom",
            "map_frame_id":   "map",
            "publish_tf":     True,
        },
    ]

    # RTAB-Map nodes expect these remapping keys for RGB-D input.
    rgbd_remappings = [
        ("rgb/image",       COLOR_TOPIC),
        ("rgb/camera_info", COLOR_INFO_TOPIC),
        ("depth/image",     DEPTH_TOPIC),
    ]

    # ------------------------------------------------------------------
    # 1. RealSense camera driver
    # ------------------------------------------------------------------
    realsense_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(realsense_launch_dir, "rs_launch.py")
        ),
        launch_arguments={
            # Align depth to colour so depth/image is spatially registered.
            "align_depth.enable": "true",
            # Enable IR emitter for structured-light depth.
            "depth_module.emitter_enabled": "1",
            # 640×360 @ 30 fps – good balance of quality vs. bandwidth.
            "rgb_camera.profile": "640x360x30",
            # Publish sensor_data (Best Effort) QoS to match RTAB-Map.
            "enable_sync": "true",
        }.items(),
    )

    # ------------------------------------------------------------------
    # 2. RGB-D Sync  (rtabmap_sync – synchronises colour + depth)
    # ------------------------------------------------------------------
    rgbd_sync_node = Node(
        package="rtabmap_sync",
        executable="rgbd_sync",
        name="rgbd_sync",
        output="screen",
        parameters=shared_params,
        remappings=rgbd_remappings,
    )

    # ------------------------------------------------------------------
    # 3. RGB-D Odometry  (rtabmap_odom)
    # ------------------------------------------------------------------
    rgbd_odom_node = Node(
        package="rtabmap_odom",
        executable="rgbd_odometry",
        name="rgbd_odometry",
        output="screen",
        parameters=shared_params,
        remappings=rgbd_remappings,
    )

    # ------------------------------------------------------------------
    # 4a. RTAB-Map SLAM  (mapping mode – default)
    # ------------------------------------------------------------------
    rtabmap_slam_node = Node(
        condition=UnlessCondition(LaunchConfiguration("localization")),
        package="rtabmap_slam",
        executable="rtabmap",
        name="rtabmap",
        output="screen",
        parameters=shared_params,
        remappings=rgbd_remappings,
        # -d deletes the previous database so each run starts from scratch
        # (controlled by delete_db_on_start argument).
        arguments=["-d"],
    )

    # ------------------------------------------------------------------
    # 4b. RTAB-Map SLAM  (localisation mode – no new map nodes)
    # ------------------------------------------------------------------
    rtabmap_loc_node = Node(
        condition=IfCondition(LaunchConfiguration("localization")),
        package="rtabmap_slam",
        executable="rtabmap",
        name="rtabmap",
        output="screen",
        parameters=[
            *shared_params,
            {
                "Mem/IncrementalMemory": "false",
                "Mem/InitWMWithAllNodes": "true",
            },
        ],
        remappings=rgbd_remappings,
    )

    # ------------------------------------------------------------------
    # 5. RTAB-Map visualiser  (optional, off by default)
    # ------------------------------------------------------------------
    rtabmap_viz_node = Node(
        condition=IfCondition(LaunchConfiguration("rtabmap_viz")),
        package="rtabmap_viz",
        executable="rtabmap_viz",
        name="rtabmap_viz",
        output="screen",
        parameters=shared_params,
        remappings=rgbd_remappings,
    )

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------
    return LaunchDescription(
        [
            # Arguments
            localization_arg,
            rtabmap_viz_arg,
            delete_db_arg,
            # Propagate use_sim_time=false (hardware run)
            SetParameter(name="use_sim_time", value=False),
            # Nodes (launch order matters: camera → sync → odom → slam)
            realsense_node,
            rgbd_sync_node,
            rgbd_odom_node,
            rtabmap_slam_node,
            rtabmap_loc_node,
            rtabmap_viz_node,
        ]
    )

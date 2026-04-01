# ugv_nav2.launch.py
#
# Launches the Nav2 autonomous navigation stack for the UGV.
#
# Prerequisite: RTAB-Map must already be running (via ugv_vslam.launch.py)
# and providing:
#   /rtabmap/grid_map  – OccupancyGrid consumed by the global costmap
#   /rtabmap/odom      – Odometry consumed by the controller and BT navigator
#   TF: map -> odom -> base_link
#
# Nodes launched:
#   controller_server   – executes velocity commands to follow a path
#   planner_server      – computes global paths (NavFn / Dijkstra)
#   behavior_server     – recovery behaviors (spin, backup, drive_on_heading, wait)
#   bt_navigator        – behavior-tree goal executor
#   waypoint_follower   – chains multiple goal poses for survey missions
#   smoother_server     – smooths computed paths
#   velocity_smoother   – limits acceleration on cmd_vel output
#   lifecycle_manager   – starts/configures/activates all Nav2 nodes as a group
#
# Usage:
#   ros2 launch ugv_bringup ugv_nav2.launch.py
#   ros2 launch ugv_bringup ugv_nav2.launch.py log_level:=debug

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    pkg_dir = get_package_share_directory('ugv_bringup')
    nav2_params = os.path.join(pkg_dir, 'config', 'nav2_params.yaml')

    log_level_arg = DeclareLaunchArgument(
        'log_level',
        default_value='info',
        description='Logging level for Nav2 nodes (debug, info, warn, error).',
    )

    log_level = LaunchConfiguration('log_level')

    # Convenience dict shared by all Nav2 nodes
    nav2_node_kwargs = dict(
        output='screen',
        parameters=[nav2_params],
        arguments=['--ros-args', '--log-level', log_level],
    )

    controller_server = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        # cmd_vel_nav -> velocity_smoother -> cmd_vel (final output to hardware)
        remappings=[('cmd_vel', 'cmd_vel_nav')],
        **nav2_node_kwargs,
    )

    planner_server = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        **nav2_node_kwargs,
    )

    behavior_server = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        **nav2_node_kwargs,
    )

    bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        **nav2_node_kwargs,
    )

    waypoint_follower = Node(
        package='nav2_waypoint_follower',
        executable='waypoint_follower',
        name='waypoint_follower',
        **nav2_node_kwargs,
    )

    smoother_server = Node(
        package='nav2_smoother',
        executable='smoother_server',
        name='smoother_server',
        **nav2_node_kwargs,
    )

    # Smooths acceleration on the final cmd_vel topic sent to the robot.
    # Receives cmd_vel_nav from the controller, outputs cmd_vel to hardware.
    velocity_smoother = Node(
        package='nav2_velocity_smoother',
        executable='velocity_smoother',
        name='velocity_smoother',
        remappings=[
            ('cmd_vel',          'cmd_vel_nav'),
            ('cmd_vel_smoothed', 'cmd_vel'),
        ],
        **nav2_node_kwargs,
    )

    # Manages the lifecycle of all Nav2 nodes above.
    # autostart: true means nodes activate automatically on launch.
    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{
            'use_sim_time': False,
            'autostart':    True,
            'node_names': [
                'controller_server',
                'planner_server',
                'behavior_server',
                'bt_navigator',
                'waypoint_follower',
                'smoother_server',
                'velocity_smoother',
            ],
        }],
    )

    return LaunchDescription([
        log_level_arg,
        controller_server,
        planner_server,
        behavior_server,
        bt_navigator,
        waypoint_follower,
        smoother_server,
        velocity_smoother,
        lifecycle_manager,
    ])

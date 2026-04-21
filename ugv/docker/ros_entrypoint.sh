#!/bin/bash
# Standard ROS 2 entrypoint: sources overlays then executes CMD.
set -e

source /opt/ros/jazzy/setup.bash
# Source the workspace install overlay if it exists.
if [ -f /ros2_ws/install/setup.bash ]; then
    source /ros2_ws/install/setup.bash
fi

exec "$@"

# ============================================================
# UGV VSLAM Docker Image
# Base  : ros:jazzy-ros-base  (Ubuntu 24.04 + ROS 2 Jazzy)
# Target: Intel RealSense RGB-D + RTAB-Map SLAM (no native SDK)
#
# Critical build flags
#   -DWITH_REALSENSE=OFF   – no librealsense2-dev on the UGV host
#   -DWITH_REALSENSE2=OFF  – same; RTAB-Map core must not link the SDK
#   -DWITH_GTSAM=OFF       – avoids GCC 13 regressions in GTSAM
#
# The RealSense *camera driver* (realsense2_camera) is installed from
# the ROS apt repository and communicates with the hardware via USB;
# RTAB-Map never needs to link against librealsense2 directly.
# ============================================================

FROM ros:jazzy-ros-base

# ── System & ROS dependencies (all explicit – no rosdep guesswork) ─────────
# Installing all known deps for rtabmap + rtabmap_ros (headless subset only).
# GUI/visualisation packages (rviz2, Qt, rtabmap_viz) are intentionally
# excluded because ros:jazzy-ros-base is a headless image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    # ── Build tools ──────────────────────────────────────────────────────
    build-essential \
    cmake \
    git \
    python3-pip \
    python3-colcon-common-extensions \
    python3-vcstool \
    # ── System math / map / DB libraries ─────────────────────────────────
    libsqlite3-dev \
    libproj-dev \
    zlib1g-dev \
    liboctomap-dev \
    libg2o-dev \
    libeigen3-dev \
    libboost-all-dev \
    # ── ROS 2 core msgs & tf ─────────────────────────────────────────────
    ros-jazzy-rclcpp \
    ros-jazzy-rclcpp-components \
    ros-jazzy-sensor-msgs \
    ros-jazzy-geometry-msgs \
    ros-jazzy-nav-msgs \
    ros-jazzy-std-msgs \
    ros-jazzy-std-srvs \
    ros-jazzy-stereo-msgs \
    ros-jazzy-visualization-msgs \
    ros-jazzy-diagnostic-updater \
    ros-jazzy-message-filters \
    ros-jazzy-pluginlib \
    ros-jazzy-tf2 \
    ros-jazzy-tf2-ros \
    ros-jazzy-tf2-geometry-msgs \
    ros-jazzy-tf2-eigen \
    ros-jazzy-tf2-sensor-msgs \
    # ── Perception / point cloud ──────────────────────────────────────────
    ros-jazzy-image-transport \
    ros-jazzy-image-transport-plugins \
    ros-jazzy-vision-opencv \
    ros-jazzy-cv-bridge \
    ros-jazzy-pcl-ros \
    ros-jazzy-pcl-conversions \
    ros-jazzy-laser-geometry \
    # ── Octomap msgs (used by rtabmap_util) ──────────────────────────────
    ros-jazzy-octomap-msgs \
    # ── RealSense ROS 2 driver (communicates via USB; no SDK link needed) ─
    ros-jazzy-realsense2-camera \
    # ── DDS middleware ────────────────────────────────────────────────────
    ros-jazzy-rmw-cyclonedds-cpp \
    && rm -rf /var/lib/apt/lists/*

# ── Workspace setup ────────────────────────────────────────────────────────
ENV ROS_WS=/ros2_ws
WORKDIR ${ROS_WS}

# Copy the workspace source tree into the image.
# .dockerignore excludes build/ install/ log/ .git/
COPY ugv/ros2_ws/src ./src

# Copy launch and config so the default CMD works without a host mount.
COPY ugv/ros2_ws/launch ./launch
COPY ugv/ros2_ws/config ./config

# ── Build workspace ────────────────────────────────────────────────────────
# Only build the SLAM-essential packages; skip GUI/demo/viz packages that
# require rviz2, Qt5, or other desktop libraries absent from ros-base.
#
# Critical flags (required – see file header for rationale):
#   -DWITH_REALSENSE=OFF   – no librealsense v1
#   -DWITH_REALSENSE2=OFF  – no librealsense2-dev on this machine
#   -DWITH_GTSAM=OFF       – GCC 13 regression workaround
RUN . /opt/ros/jazzy/setup.sh && \
    MAKEFLAGS="-j2" colcon build \
        --symlink-install \
        --packages-select \
            rtabmap \
            rtabmap_msgs \
            rtabmap_conversions \
            rtabmap_sync \
            rtabmap_odom \
            rtabmap_slam \
            rtabmap_util \
            rtabmap_ros \
        --cmake-args \
            -DWITH_REALSENSE=OFF \
            -DWITH_REALSENSE2=OFF \
            -DWITH_GTSAM=OFF \
            -DCMAKE_BUILD_TYPE=Release \
        --event-handlers console_direct+ \
    && rm -rf build/ log/

# ── Runtime environment ────────────────────────────────────────────────────
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# Source workspace overlay on every shell / entrypoint invocation.
RUN echo "source /opt/ros/jazzy/setup.bash" >> /root/.bashrc && \
    echo "source ${ROS_WS}/install/setup.bash" >> /root/.bashrc

# Use the official ROS entrypoint so ros__parameters work correctly.
COPY ugv/docker/ros_entrypoint.sh /ros_entrypoint.sh
RUN chmod +x /ros_entrypoint.sh
ENTRYPOINT ["/ros_entrypoint.sh"]

# Default command: launch full VSLAM stack.
# Override at runtime with: docker run ... ros2 launch ugv_vslam ugv_vslam.launch.py
CMD ["ros2", "launch", "ugv_vslam", "ugv_vslam.launch.py"]

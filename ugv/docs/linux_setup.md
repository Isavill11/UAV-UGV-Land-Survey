# UGV Linux Machine Setup Guide

Complete step-by-step instructions for setting up and running the UGV autonomous
stack on the integration Linux computer.

**Target environment:**
- OS: Ubuntu 24.04 LTS
- ROS: ROS 2 Jazzy Jalisco
- Hardware: Intel RealSense D4xx camera connected via USB

---

## Table of Contents

1. [Install ROS 2 Jazzy](#1-install-ros-2-jazzy)
2. [Install system dependencies](#2-install-system-dependencies)
3. [Clone the repository](#3-clone-the-repository)
4. [Initialize git submodules](#4-initialize-git-submodules)
5. [Install ROS package dependencies](#5-install-ros-package-dependencies)
6. [Build the workspace](#6-build-the-workspace)
7. [Source the workspace](#7-source-the-workspace)
8. [Configure the camera mounting transform](#8-configure-the-camera-mounting-transform)
9. [Verify the RealSense camera](#9-verify-the-realsense-camera)
10. [Run the stack](#10-run-the-stack)
11. [Verify the running stack](#11-verify-the-running-stack)
12. [Sending navigation goals](#12-sending-navigation-goals)
13. [Updating after a git pull](#13-updating-after-a-git-pull)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Install ROS 2 Jazzy

Skip this section if ROS 2 Jazzy is already installed
(`ros2 --version` should print `jazzy`).

```bash
# Add the ROS 2 apt repository
sudo apt install -y software-properties-common curl
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) \
    signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
    http://packages.ros.org/ros2/ubuntu \
    $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
    | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

sudo apt update
sudo apt install -y ros-jazzy-ros-base python3-argcomplete
```

Add ROS to your shell so it is sourced automatically in every new terminal:

```bash
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

Verify:

```bash
ros2 --version
# Expected: ros2 jazzy
```

---

## 2. Install system dependencies

### Build tools

```bash
sudo apt install -y \
    build-essential \
    cmake \
    git \
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-vcstool
```

### C++ libraries required by RTAB-Map

These are compiled from source (submodules), so their native deps must be
present on the system:

```bash
sudo apt install -y \
    libsqlite3-dev \
    libproj-dev \
    zlib1g-dev \
    liboctomap-dev \
    libg2o-dev \
    libeigen3-dev \
    libboost-all-dev \
    libpcl-dev \
    libopencv-dev
```

### USB rules for the RealSense camera

The RealSense driver requires udev rules so the camera is accessible without
root privileges:

```bash
sudo apt install -y udev
# The rules are shipped with ros-jazzy-realsense2-camera (installed later).
# After installing that package, reload udev:
sudo udevadm control --reload-rules
sudo udevadm trigger
```

---

## 3. Clone the repository

```bash
# Replace <repo-url> with the actual GitHub URL of this project.
git clone --recurse-submodules <repo-url>
cd UAV-UGV-Land-Survey
```

The `--recurse-submodules` flag is mandatory. Without it, the `rtabmap` and
`rtabmap_ros` source directories will be empty and the build will fail.

If you already cloned without the flag:

```bash
git submodule update --init --recursive
```

Confirm the submodules are populated:

```bash
ls ugv/ros2_ws/src/rtabmap/CMakeLists.txt
ls ugv/ros2_ws/src/rtabmap_ros/
# Both should show files, not "No such file or directory".
```

---

## 4. Initialize git submodules

If you ever update the repo with `git pull` and the submodule pointers change,
re-run this to sync them:

```bash
git submodule update --init --recursive
```

---

## 5. Install ROS package dependencies

### Initialize rosdep (once per machine)

```bash
sudo rosdep init        # skip if it says "already initialized"
rosdep update --rosdistro jazzy
```

### Install Nav2 and all ROS packages

```bash
sudo apt install -y \
    ros-jazzy-realsense2-camera \
    ros-jazzy-rmw-cyclonedds-cpp \
    ros-jazzy-pcl-ros \
    ros-jazzy-pcl-conversions \
    ros-jazzy-cv-bridge \
    ros-jazzy-image-transport \
    ros-jazzy-image-transport-plugins \
    ros-jazzy-vision-opencv \
    ros-jazzy-tf2 \
    ros-jazzy-tf2-ros \
    ros-jazzy-tf2-geometry-msgs \
    ros-jazzy-tf2-eigen \
    ros-jazzy-tf2-sensor-msgs \
    ros-jazzy-sensor-msgs \
    ros-jazzy-geometry-msgs \
    ros-jazzy-nav-msgs \
    ros-jazzy-std-msgs \
    ros-jazzy-std-srvs \
    ros-jazzy-diagnostic-updater \
    ros-jazzy-message-filters \
    ros-jazzy-pluginlib \
    ros-jazzy-laser-geometry \
    ros-jazzy-octomap-msgs \
    ros-jazzy-nav2-bt-navigator \
    ros-jazzy-nav2-controller \
    ros-jazzy-nav2-planner \
    ros-jazzy-nav2-behaviors \
    ros-jazzy-nav2-waypoint-follower \
    ros-jazzy-nav2-lifecycle-manager \
    ros-jazzy-nav2-costmap-2d \
    ros-jazzy-nav2-navfn-planner \
    ros-jazzy-nav2-smoother \
    ros-jazzy-nav2-velocity-smoother \
    ros-jazzy-nav2-regulated-pure-pursuit-controller \
    ros-jazzy-nav2-map-server \
    ros-jazzy-robot-localization \
    ros-jazzy-rclcpp \
    ros-jazzy-rclcpp-components
```

### Reload udev rules (after realsense2-camera is installed)

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Install workspace rosdep deps

```bash
cd ugv/ros2_ws
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
```

---

## 6. Build the workspace

Navigate to the ROS 2 workspace and build. The three CMake flags are
**mandatory** — do not omit them.

```bash
cd ugv/ros2_ws
source /opt/ros/jazzy/setup.bash

colcon build \
    --symlink-install \
    --cmake-args \
        -DWITH_REALSENSE=OFF \
        -DWITH_REALSENSE2=OFF \
        -DWITH_GTSAM=OFF \
        -DCMAKE_BUILD_TYPE=Release \
    --event-handlers console_direct+
```

**Flag reference:**

| Flag | Reason |
|---|---|
| `-DWITH_REALSENSE=OFF` | No librealsense v1 on this machine |
| `-DWITH_REALSENSE2=OFF` | RTAB-Map core must not link librealsense2 SDK directly |
| `-DWITH_GTSAM=OFF` | Avoids GCC 13 regressions in GTSAM |
| `--symlink-install` | Python/launch files update without rebuilding |

RTAB-Map compiles a large amount of C++ code. On a machine with limited RAM,
limit parallel jobs to avoid an out-of-memory kill:

```bash
MAKEFLAGS="-j2" colcon build \
    --symlink-install \
    --cmake-args \
        -DWITH_REALSENSE=OFF \
        -DWITH_REALSENSE2=OFF \
        -DWITH_GTSAM=OFF \
        -DCMAKE_BUILD_TYPE=Release
```

A successful build ends with:

```
Summary: X packages finished [...]
```

If any package fails, check the log:

```bash
cat log/latest_build/<package_name>/stderr.log
```

---

## 7. Source the workspace

After a successful build, source the install overlay. Do this in every new
terminal before using ROS 2 commands, or add it to `~/.bashrc` permanently:

```bash
source ugv/ros2_ws/install/setup.bash
```

To add permanently (run once):

```bash
# Run from the repo root
echo "source $(pwd)/ugv/ros2_ws/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

Verify the package is found:

```bash
ros2 pkg list | grep ugv_bringup
# Expected: ugv_bringup
```

---

## 8. Configure the camera mounting transform

Before running on the physical robot, update the static transform that describes
where the RealSense camera is mounted relative to the robot's centre
(`base_link`).

Open the full stack launch file:

```
ugv/ros2_ws/src/ugv_bringup/launch/ugv_full_stack.launch.py
```

Find the `static_transform_publisher` node arguments (around line 60):

```python
arguments=[
    '0.15', '0.0', '0.25',   # x  y  z  (metres)
    '0.0',  '0.0', '0.0',    # yaw  pitch  roll  (radians)
    'base_link', 'camera_link',
],
```

Replace the values with your actual measurements:

- `x` — how far **forward** the camera is from the robot centre (metres)
- `y` — how far **left** (positive) or **right** (negative) of centre (metres)
- `z` — how far **up** from the base_link origin (metres)
- `yaw/pitch/roll` — rotation in radians; 0 for a level, forward-facing camera

Similarly update `robot_radius` in:

```
ugv/ros2_ws/src/ugv_bringup/config/nav2_params.yaml
```

Set it to half the widest dimension of your UGV (in metres).

After editing, if you used `--symlink-install` during the build the changes
take effect immediately (no rebuild needed). Otherwise rebuild:

```bash
cd ugv/ros2_ws
colcon build --symlink-install \
    --packages-select ugv_bringup \
    --cmake-args -DWITH_REALSENSE=OFF -DWITH_REALSENSE2=OFF -DWITH_GTSAM=OFF
```

---

## 9. Verify the RealSense camera

Plug the RealSense D4xx in via USB 3.0 and confirm the system detects it:

```bash
lsusb | grep -i intel
# Expected: something like "Intel Corp. RealSense D435"
```

Check kernel recognises it:

```bash
dmesg | grep -i realsense | tail -5
```

Quick stream test (streams for 5 seconds then exits):

```bash
ros2 launch realsense2_camera rs_launch.py \
    align_depth.enable:=true &
sleep 5
ros2 topic list | grep camera
# Expected lines include:
#   /camera/camera/color/image_raw
#   /camera/camera/aligned_depth_to_color/image_raw
kill %1
```

---

## 10. Run the stack

Open a dedicated terminal for each command below. Source the workspace in every
new terminal before running.

### Option A — Full autonomous stack (recommended)

Brings up VSLAM + Nav2 in one command:

```bash
source ugv/ros2_ws/install/setup.bash
ros2 launch ugv_bringup ugv_full_stack.launch.py
```

To start in **localisation-only mode** (uses an existing map from a previous
run, does not create new map nodes):

```bash
ros2 launch ugv_bringup ugv_full_stack.launch.py localization:=true
```

### Option B — VSLAM only (no navigation)

Useful for verifying the camera and SLAM pipeline in isolation:

```bash
source ugv/ros2_ws/install/setup.bash
ros2 launch ugv_bringup ugv_vslam.launch.py
```

### Option C — Run VSLAM and Nav2 in separate terminals

Terminal 1 — VSLAM:

```bash
source ugv/ros2_ws/install/setup.bash
ros2 launch ugv_bringup ugv_vslam.launch.py
```

Terminal 2 — Nav2 (start only after RTAB-Map is publishing):

```bash
source ugv/ros2_ws/install/setup.bash
ros2 launch ugv_bringup ugv_nav2.launch.py
```

---

## 11. Verify the running stack

Run the smoke-test script in a new terminal while the stack is running:

```bash
source ugv/ros2_ws/install/setup.bash
bash ugv/ros2_ws/scripts/verify_vslam.sh
```

Expected output (all green):

```
[PASS] Node /rgbd_sync is alive
[PASS] Node /rgbd_odometry is alive
[PASS] Node /rtabmap is alive
[PASS] /camera/camera/color/image_raw: 29.9 Hz
[PASS] /camera/camera/aligned_depth_to_color/image_raw: 29.9 Hz
[PASS] /rtabmap/odom: 28.5 Hz
[PASS] TF: map -> odom is broadcasting
[PASS] TF: odom -> base_link is broadcasting
[PASS] TF: map -> base_link is broadcasting
All checks passed.
```

### Additional manual checks

Check all expected topics exist:

```bash
ros2 topic list | grep -E "rtabmap|camera|cmd_vel"
```

Check the TF tree is complete:

```bash
ros2 run tf2_tools view_frames
# Generates frames.pdf in the current directory showing the full TF tree.
```

Check Nav2 lifecycle nodes are active:

```bash
ros2 lifecycle list /controller_server
ros2 lifecycle list /bt_navigator
# Both should show: active
```

Check the map is being published:

```bash
ros2 topic hz /rtabmap/grid_map
# Expected: ~1 Hz
```

---

## 12. Sending navigation goals

### Single goal via command line

```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 1.0, y: 0.5, z: 0.0}, orientation: {w: 1.0}}}}"
```

Replace `x: 1.0, y: 0.5` with the target coordinates in the map frame.

### Series of waypoints (survey pattern)

```bash
ros2 action send_goal /follow_waypoints nav2_msgs/action/FollowWaypoints \
  "{poses: [
      {header: {frame_id: 'map'}, pose: {position: {x: 1.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}},
      {header: {frame_id: 'map'}, pose: {position: {x: 2.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}},
      {header: {frame_id: 'map'}, pose: {position: {x: 2.0, y: 1.0, z: 0.0}, orientation: {w: 1.0}}}
  ]}"
```

### Cancel an active goal

```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{}" --cancel-after-send
```

---

## 13. Updating after a git pull

After pulling new changes from the repository:

```bash
git pull
git submodule update --init --recursive   # always run this after a pull
```

Then rebuild only what changed:

```bash
cd ugv/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install \
    --cmake-args -DWITH_REALSENSE=OFF -DWITH_REALSENSE2=OFF -DWITH_GTSAM=OFF

source install/setup.bash
```

If only `ugv_bringup` changed (launch files, configs, no C++ changes):

```bash
colcon build --symlink-install \
    --packages-select ugv_bringup \
    --cmake-args -DWITH_REALSENSE=OFF -DWITH_REALSENSE2=OFF -DWITH_GTSAM=OFF
```

---

## 14. Troubleshooting

### Build killed (Out of Memory)

Limit parallel jobs:

```bash
MAKEFLAGS="-j2" colcon build --symlink-install \
    --cmake-args -DWITH_REALSENSE=OFF -DWITH_REALSENSE2=OFF -DWITH_GTSAM=OFF
```

### `Package 'ugv_bringup' not found`

The workspace overlay was not sourced:

```bash
source ugv/ros2_ws/install/setup.bash
```

### Camera not detected inside the stack

```bash
# Confirm kernel sees the camera
lsusb | grep -i intel

# Confirm permission (should not require sudo)
ros2 launch realsense2_camera rs_launch.py

# If permission denied, reload udev rules
sudo udevadm control --reload-rules && sudo udevadm trigger
# Then unplug and replug the camera.
```

### No depth messages / depth not aligned to colour

Confirm `align_depth.enable:=true` is in `ugv_vslam.launch.py` (it is by
default). Also ensure the camera is not streaming colour and depth at
mismatched resolutions — the default `640x360x30` profile handles both.

### TF `map -> odom` missing

RTAB-Map needs to initialise before it broadcasts this transform. Wait 5–10
seconds after launch. If it never appears:

```bash
ros2 topic echo /rtabmap/odom --once
# If no output, the odometry node is not receiving camera frames.
# Check that /camera/camera/color/image_raw and the depth topic are publishing.
```

### Nav2 nodes stuck in `inactive` state

The lifecycle manager should auto-activate all nodes. If they remain inactive:

```bash
# Manually trigger activation
ros2 lifecycle set /controller_server activate
ros2 lifecycle set /planner_server activate
ros2 lifecycle set /bt_navigator activate
ros2 lifecycle set /behavior_server activate
ros2 lifecycle set /waypoint_follower activate
```

### Nav2 cannot find a path

- The map may not have enough coverage yet — drive the robot around to build
  the map before sending goals.
- Check `allow_unknown: true` is set in `nav2_params.yaml` under
  `GridBased` (it is by default), which allows planning through unexplored cells.
- Increase `inflation_radius` if the robot considers itself in collision at
  the start or goal pose.

### `colcon build` fails with GTSAM or RealSense errors

Confirm all three flags are present and the build directory is clean:

```bash
rm -rf ugv/ros2_ws/build ugv/ros2_ws/install ugv/ros2_ws/log
# Then rebuild from scratch.
```

### DDS discovery issues (UGV not visible from other machines on the network)

Confirm CycloneDDS is set as the middleware:

```bash
echo $RMW_IMPLEMENTATION
# Expected: rmw_cyclonedds_cpp

# If not set, add to ~/.bashrc:
echo "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" >> ~/.bashrc
source ~/.bashrc
```

Confirm the machines are on the same LAN and no firewall is blocking UDP
multicast (ports 7400–7500 are used by DDS discovery).

# UGV ROS 2 Workspace

RGB-D VSLAM bring-up for the UGV using **RTAB-Map** on **ROS 2 Jazzy / Ubuntu 24.04**.

Hardware: Intel RealSense D4xx series (depth aligned via `realsense2_camera` driver).

---

## Directory Layout

```
ugv/ros2_ws/
├── config/
│   └── rtabmap_params.yaml     # RTAB-Map / odometry / sync parameters
├── launch/
│   └── ugv_vslam.launch.py     # Full VSLAM bring-up (camera + odom + SLAM)
├── scripts/
│   └── verify_vslam.sh         # Topic-rate and TF-tree smoke test
└── src/
    ├── rtabmap/                 # RTAB-Map core library (submodule)
    └── rtabmap_ros/             # RTAB-Map ROS 2 packages (submodule)
```

---

## Critical Build Flags

The UGV computer does **not** have `librealsense2-dev` installed at the OS level.
RTAB-Map must be compiled with the RealSense SDK and GTSAM **disabled**:

| Flag | Reason |
|---|---|
| `-DWITH_REALSENSE=OFF` | No librealsense v1 |
| `-DWITH_REALSENSE2=OFF` | No librealsense2-dev on host |
| `-DWITH_GTSAM=OFF` | GCC 13 regression workaround |

These flags are baked into the Docker image and must be passed for every native build.

---

## Option A — Native Build (Ubuntu 24.04 + ROS 2 Jazzy)

### 1. Install system dependencies

```bash
sudo apt update
sudo apt install -y \
    ros-jazzy-realsense2-camera \
    ros-jazzy-rmw-cyclonedds-cpp \
    ros-jazzy-pcl-ros \
    ros-jazzy-cv-bridge \
    ros-jazzy-image-transport \
    ros-jazzy-tf2-ros \
    python3-rosdep \
    python3-colcon-common-extensions
```

### 2. Initialise rosdep

```bash
sudo rosdep init   # skip if already done
rosdep update --rosdistro jazzy
```

### 3. Install workspace dependencies

```bash
cd ugv/ros2_ws
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
```

### 4. Build with required CMake flags

```bash
source /opt/ros/jazzy/setup.bash

colcon build \
    --symlink-install \
    --cmake-args \
        -DWITH_REALSENSE=OFF \
        -DWITH_REALSENSE2=OFF \
        -DWITH_GTSAM=OFF \
        -DCMAKE_BUILD_TYPE=Release
```

### 5. Source the workspace

```bash
source install/setup.bash
```

### 6. Launch VSLAM

```bash
# Mapping mode (default) -- deletes previous database on start
ros2 launch ugv_vslam ugv_vslam.launch.py

# Localisation only (requires existing ~/.ros/rtabmap.db)
ros2 launch ugv_vslam ugv_vslam.launch.py localization:=true

# With RTAB-Map's built-in visualiser
ros2 launch ugv_vslam ugv_vslam.launch.py rtabmap_viz:=true
```

---

## Option B — Docker Build

### Prerequisites

- Docker Engine >= 24 and Docker Compose v2
- RealSense camera connected via USB

### 1. Build the image

Run from the **repository root** (build context must include `ugv/`):

```bash
docker compose -f ugv/docker/docker-compose.ugv.yml build
```

The build compiles RTAB-Map with:
```
-DWITH_REALSENSE=OFF -DWITH_REALSENSE2=OFF -DWITH_GTSAM=OFF
```

### 2. Launch

```bash
docker compose -f ugv/docker/docker-compose.ugv.yml up
```

### 3. Override command (e.g. localisation)

```bash
docker compose -f ugv/docker/docker-compose.ugv.yml run ugv_vslam \
    ros2 launch ugv_vslam ugv_vslam.launch.py localization:=true
```

### 4. Open an interactive shell in the running container

```bash
docker compose -f ugv/docker/docker-compose.ugv.yml exec ugv_vslam bash
```

---

## Verification

With the VSLAM stack running (native or Docker), run the smoke-test script in a separate terminal:

```bash
# Native
source ugv/ros2_ws/install/setup.bash
bash ugv/ros2_ws/scripts/verify_vslam.sh

# Inside the container
bash /ros2_ws/scripts/verify_vslam.sh
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

---

## TF Tree

```
map
 └── odom          (published by rtabmap_slam / rtabmap node)
      └── base_link (published by rtabmap_odom / rgbd_odometry node)
                    └── camera_link  (published by realsense2_camera)
```

---

## Key Topics

| Topic | Type | Publisher |
|---|---|---|
| `/camera/camera/color/image_raw` | `sensor_msgs/Image` | realsense2_camera |
| `/camera/camera/color/camera_info` | `sensor_msgs/CameraInfo` | realsense2_camera |
| `/camera/camera/aligned_depth_to_color/image_raw` | `sensor_msgs/Image` | realsense2_camera |
| `/rtabmap/odom` | `nav_msgs/Odometry` | rgbd_odometry |
| `/rtabmap/map` | `nav_msgs/OccupancyGrid` | rtabmap |
| `/rtabmap/mapData` | `rtabmap_msgs/MapData` | rtabmap |

---

## Troubleshooting

**Camera not found inside Docker**
- Ensure `privileged: true` and the USB device mounts in `docker-compose.ugv.yml`.
- Check `dmesg | grep -i realsense` on the host.

**No depth messages**
- Confirm `align_depth.enable: true` is passed to `rs_launch.py`.
- Verify the camera is not streaming depth at a different resolution than colour.

**TF `map -> odom` missing**
- RTAB-Map needs at least one successful loop closure or a prior database.
- Run in mapping mode first, drive a short loop, then switch to localisation.

**Build fails with GTSAM/RealSense errors**
- Confirm all three CMake flags are present: `-DWITH_REALSENSE=OFF -DWITH_REALSENSE2=OFF -DWITH_GTSAM=OFF`.
- Delete the `build/` directory and rebuild from scratch.

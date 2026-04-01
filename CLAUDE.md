# UAV-UGV Land Survey — Claude Code Notes

## Environment

- **OS:** Ubuntu 24.04
- **ROS version:** ROS 2 Jazzy

## Workspace

The ROS 2 workspace is located at `ugv/ros2_ws`. All package development, builds, and sourcing happen inside this directory.

## Build Requirements

All builds must include the following CMake flags:

```bash
colcon build --cmake-args -DWITH_REALSENSE=OFF -DWITH_GTSAM=OFF
```

Never build without these flags — they disable hardware/library dependencies that are not available in this environment.

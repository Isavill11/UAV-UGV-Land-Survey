cmake_minimum_required(VERSION 3.5)
project(ugv_ackermann)

find_package(ament_cmake REQUIRED)
find_package(rclpy REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(PROGRAMS
  ugv_ackermann/ackermann_converter_node.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()

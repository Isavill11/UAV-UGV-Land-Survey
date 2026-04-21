#!/usr/bin/env python3
"""Ackermann converter node.

Subscribes to /cmd_vel (Twist) and publishes steering + speed commands.
This example uses std_msgs/Float64 outputs to represent:
- /steer_angle (radians)
- /drive_velocity (forward m/s)

For your real hardware, replace publishers with the specific interface topics.
"""

from math import atan2

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp a value between limits."""
    return max(min_value, min(max_value, value))


class AckermannConverterNode(Node):
    def __init__(self):
        super().__init__('ackermann_converter')

        # Parameters that can be tuned remotely or from launch.
        self.declare_parameter('wheel_base', 0.45)
        self.declare_parameter('max_steer_angle', 0.6)
        self.declare_parameter('max_speed', 1.0)

        self.wheel_base = self.get_parameter('wheel_base').value
        self.max_steer_angle = self.get_parameter('max_steer_angle').value
        self.max_speed = self.get_parameter('max_speed').value

        # Input twist from nav2 /cmd_vel.
        self.cmd_vel_sub = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10,
        )

        # Output steering angle in radians and drive speed m/s.
        # Replace with your robot-specific command topics/joint interfaces.
        self.steer_pub = self.create_publisher(Float64, '/steer_angle', 10)
        self.speed_pub = self.create_publisher(Float64, '/drive_velocity', 10)

    def cmd_vel_callback(self, msg: Twist) -> None:
        """Convert cmd_vel Twist into steering and drive commands."""
        # For Ackermann kinematics: curvature = omega / v. steering = atan(wheel_base * curvature)
        linear = msg.linear.x
        angular = msg.angular.z

        # If linear speed is near zero, keep steering 0 to avoid large values.
        if abs(linear) < 1e-4:
            steer_angle = 0.0
        else:
            curvature = angular / linear
            steer_angle = atan2(curvature * self.wheel_base, 1.0)

        # Clamp outputs to safe limits.
        steer_angle = clamp(steer_angle, -self.max_steer_angle, self.max_steer_angle)
        speed = clamp(linear, -self.max_speed, self.max_speed)

        # Publish commands.
        steer_msg = Float64()
        steer_msg.data = steer_angle
        self.steer_pub.publish(steer_msg)

        speed_msg = Float64()
        speed_msg.data = speed
        self.speed_pub.publish(speed_msg)

        self.get_logger().debug(
            f"cmd_vel linear={linear:.3f} angular={angular:.3f} -> steer={steer_angle:.3f}, speed={speed:.3f}"
        )


def main(args=None):
    rclpy.init(args=args)
    node = AckermannConverterNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

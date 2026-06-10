"""Simple teleop: /cmd_vel -> /hw/joint_commands (ruedas solo, sin dirección)."""

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray

NUM_JOINTS = 8


class TeleopJointCommandsNode(Node):
    def __init__(self) -> None:
        super().__init__("teleop_joint_commands_node")

        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("joint_commands_topic", "/hw/joint_commands")
        self.declare_parameter("wheel_radius", 0.052)
        self.declare_parameter("track_width", 0.33)
        self.declare_parameter("publish_rate_hz", 50.0)
        self.declare_parameter("cmd_vel_timeout_sec", 0.5)

        self.cmd_vel_topic = str(self.get_parameter("cmd_vel_topic").value)
        self.joint_commands_topic = str(self.get_parameter("joint_commands_topic").value)
        self.wheel_radius = float(self.get_parameter("wheel_radius").value)
        self.track_width = float(self.get_parameter("track_width").value)
        self.publish_rate_hz = float(self.get_parameter("publish_rate_hz").value)
        self.cmd_vel_timeout_sec = float(self.get_parameter("cmd_vel_timeout_sec").value)

        self.latest_cmd_vel = Twist()
        self.last_cmd_vel_time = None

        self.publisher = self.create_publisher(Float64MultiArray, self.joint_commands_topic, 10)
        self.create_subscription(Twist, self.cmd_vel_topic, self.cmd_vel_callback, 10)
        self.create_timer(1.0 / self.publish_rate_hz, self.publish_callback)

        self.get_logger().info(
            "%s -> %s (solo velocidad de ruedas)" % (self.cmd_vel_topic, self.joint_commands_topic)
        )

    def cmd_vel_callback(self, message: Twist) -> None:
        self.latest_cmd_vel = message
        self.last_cmd_vel_time = self.get_clock().now()

    def publish_callback(self) -> None:
        msg = Float64MultiArray()
        msg.data = [0.0] * NUM_JOINTS

        if self.last_cmd_vel_time is None:
            self.publisher.publish(msg)
            return

        age = (self.get_clock().now() - self.last_cmd_vel_time).nanoseconds * 1e-9
        if age > self.cmd_vel_timeout_sec:
            self.publisher.publish(msg)
            return

        vx = float(self.latest_cmd_vel.linear.x)
        omega = float(self.latest_cmd_vel.angular.z)

        # m/s y rad/s del cuerpo -> rad/s de rueda (diff drive simple)
        half_track = 0.5 * self.track_width
        left = (vx - omega * half_track) / self.wheel_radius
        right = (vx + omega * half_track) / self.wheel_radius

        # [steer x4] + [f_left, f_right, b_left, b_right]
        msg.data[4] = left
        msg.data[5] = right
        msg.data[6] = left
        msg.data[7] = right

        self.publisher.publish(msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = TeleopJointCommandsNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

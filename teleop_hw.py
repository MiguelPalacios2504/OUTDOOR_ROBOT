#!/usr/bin/env python3
import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import Float64MultiArray

# /hw/joint_commands — orden firmware ESP32
# [0-3] servos rad  |  [4-7] motores rad/s (f_left, f_right, b_left, b_right)

WHEEL_R = 0.052
RATE_HZ = 50.0
CMD_TIMEOUT = 0.5


class TeleopHw(Node):
    def __init__(self):
        super().__init__("teleop_hw")

        pub_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        sub_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)

        self.cmd = Twist()
        self.have_cmd = False
        self.last_cmd_time = None

        self.pub = self.create_publisher(Float64MultiArray, "/hw/joint_commands", pub_qos)
        self.create_subscription(Twist, "/cmd_vel", self.on_cmd_vel, sub_qos)
        self.create_timer(1.0 / RATE_HZ, self.on_timer)

        self.get_logger().info("Publicando /hw/joint_commands a %.0f Hz (esperando /cmd_vel)" % RATE_HZ)

    def on_cmd_vel(self, msg: Twist):
        self.cmd = msg
        self.have_cmd = True
        self.last_cmd_time = self.get_clock().now()

    def on_timer(self):
        out = Float64MultiArray()
        out.data = [0.0] * 8

        if self.have_cmd and self.last_cmd_time is not None:
            age = (self.get_clock().now() - self.last_cmd_time).nanoseconds * 1e-9
            if age <= CMD_TIMEOUT:
                vx = float(self.cmd.linear.x)
                wz = float(self.cmd.angular.z)
                left = (vx - 0.5 * wz) / WHEEL_R
                right = (vx + 0.5 * wz) / WHEEL_R
                out.data[4] = left
                out.data[5] = right
                out.data[6] = left
                out.data[7] = right

        self.pub.publish(out)


def main():
    rclpy.init()
    node = TeleopHw()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

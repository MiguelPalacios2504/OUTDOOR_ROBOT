#!/usr/bin/env python3
import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray

# /hw/joint_commands — mismo orden que el firmware ESP32
# [0] servo1  f_left_steer   rad
# [1] servo2  f_right_steer  rad
# [2] servo3  b_leftsteer    rad
# [3] servo4  b_rightsteer   rad
# [4] motor1  f_leftwheel    rad/s
# [5] motor2  f_rightwheel   rad/s
# [6] motor3  b_leftwheel    rad/s
# [7] motor4  b_rightwheel   rad/s

WHEEL_R = 0.052


class TeleopHw(Node):
    def __init__(self):
        super().__init__("teleop_hw")
        self.pub = self.create_publisher(Float64MultiArray, "/hw/joint_commands", 10)
        self.create_subscription(Twist, "/cmd_vel", self.cb, 10)

    def cb(self, msg: Twist):
        vx = float(msg.linear.x)
        wz = float(msg.angular.z)

        left = (vx - 0.5 * wz) / WHEEL_R
        right = (vx + 0.5 * wz) / WHEEL_R

        out = Float64MultiArray()
        out.data = [
            0.0, 0.0, 0.0, 0.0,
            left, right, left, right,
        ]
        self.pub.publish(out)


def main():
    rclpy.init()
    node = TeleopHw()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()

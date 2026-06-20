
import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray

WHEEL_RADIUS = 0.052
TRACK_WIDTH = 0.33
TIMEOUT_SEC = 0.5
RATE_HZ = 50.0


class TeleopHw(Node):
    def __init__(self):
        super().__init__("teleop_hw")
        self.cmd = Twist()
        self.last_cmd_time = None
        self.pub = self.create_publisher(Float64MultiArray, "/hw/joint_commands", 10)
        self.create_subscription(Twist, "/cmd_vel", self.on_cmd_vel, 10)
        self.create_timer(1.0 / RATE_HZ, self.on_timer)

    def on_cmd_vel(self, msg: Twist):
        self.cmd = msg
        self.last_cmd_time = self.get_clock().now()

    def on_timer(self):
        out = Float64MultiArray()
        out.data = [0.0] * 8

        if self.last_cmd_time is None:
            self.pub.publish(out)
            return

        age = (self.get_clock().now() - self.last_cmd_time).nanoseconds * 1e-9
        if age > TIMEOUT_SEC:
            self.pub.publish(out)
            return

        vx = float(self.cmd.linear.x)
        omega = float(self.cmd.angular.z)
        half = 0.5 * TRACK_WIDTH
        left = (vx - omega * half) / WHEEL_RADIUS
        right = (vx + omega * half) / WHEEL_RADIUS

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

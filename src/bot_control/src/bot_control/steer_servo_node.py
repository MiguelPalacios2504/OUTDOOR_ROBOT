"""Drive 4 Feetech STS/ST steering servos on the Raspberry Pi."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import List, Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray

from bot_control.sts_servo_bus import (
    StsServoBus,
    calibrated_angle_to_counts,
    calibrated_counts_to_rad,
)

STEER_JOINT_COUNT = 4
STEER_JOINT_NAMES = (
    "f_left_steer",
    "f_right_steer",
    "b_leftsteer",
    "b_rightsteer",
)


@dataclass
class SteerChannel:
    name: str
    port: str
    servo_id: int
    joint_index: int
    bus: StsServoBus


class SteerServoNode(Node):
    def __init__(self) -> None:
        super().__init__("steer_servo_node")

        self.declare_parameter("use_single_bus", True)
        self.declare_parameter("serial_port", "/dev/ttyACM0")
        self.declare_parameter(
            "serial_ports",
            ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyACM2", "/dev/ttyACM3"],
        )
        self.declare_parameter("baud_rate", 1_000_000)
        self.declare_parameter("protocol_end", 1)
        # Orden joints: f_left, f_right, b_left, b_right
        self.declare_parameter("servo_ids", [11, 14, 12, 13])
        self.declare_parameter("center_counts", [1778, 1173, 1206, 1551])
        self.declare_parameter("counts_plus_90", [2792, 2196, 2163, 2599])
        self.declare_parameter("counts_minus_90", [697, 152, 123, 626])
        self.declare_parameter("move_time_ms", 400)
        self.declare_parameter("move_acc", 20)
        self.declare_parameter("control_rate_hz", 50.0)
        self.declare_parameter("command_timeout_sec", 0.5)
        self.declare_parameter("steering_angle_limit_deg", 45.0)
        self.declare_parameter("ping_retries", 3)
        self.declare_parameter("require_all_servos", True)
        self.declare_parameter("joint_commands_topic", "/hw/joint_commands")
        self.declare_parameter("steer_states_topic", "/hw/steer_states")

        use_single_bus = bool(self.get_parameter("use_single_bus").value)
        serial_port = str(self.get_parameter("serial_port").value)
        serial_ports = [str(v) for v in self.get_parameter("serial_ports").value]
        baud_rate = int(self.get_parameter("baud_rate").value)
        protocol_end = int(self.get_parameter("protocol_end").value)
        servo_ids = [int(v) for v in self.get_parameter("servo_ids").value]
        self._center_counts = [int(v) for v in self.get_parameter("center_counts").value]
        self._counts_plus_90 = [int(v) for v in self.get_parameter("counts_plus_90").value]
        self._counts_minus_90 = [int(v) for v in self.get_parameter("counts_minus_90").value]
        self.move_time_ms = int(self.get_parameter("move_time_ms").value)
        self.move_acc = int(self.get_parameter("move_acc").value)
        self.control_rate_hz = float(self.get_parameter("control_rate_hz").value)
        self.command_timeout_sec = float(self.get_parameter("command_timeout_sec").value)
        self.steering_angle_limit_rad = math.radians(
            float(self.get_parameter("steering_angle_limit_deg").value)
        )
        self.ping_retries = int(self.get_parameter("ping_retries").value)
        self.require_all_servos = bool(self.get_parameter("require_all_servos").value)
        self.joint_commands_topic = str(self.get_parameter("joint_commands_topic").value)
        self.steer_states_topic = str(self.get_parameter("steer_states_topic").value)
        self._use_single_bus = use_single_bus
        self._shared_bus: Optional[StsServoBus] = None

        for name, values in (
            ("servo_ids", servo_ids),
            ("center_counts", self._center_counts),
            ("counts_plus_90", self._counts_plus_90),
            ("counts_minus_90", self._counts_minus_90),
        ):
            if len(values) != STEER_JOINT_COUNT:
                raise ValueError(f"{name} must contain exactly 4 values")
        if not use_single_bus and len(serial_ports) != STEER_JOINT_COUNT:
            raise ValueError("serial_ports must contain exactly 4 values in multi_usb mode")

        self._target_angles = [0.0] * STEER_JOINT_COUNT
        self._last_cmd_time = None
        self._channels: List[SteerChannel] = []
        self._ready = False

        if use_single_bus:
            self._shared_bus = StsServoBus(serial_port, baud_rate, protocol_end)
            self._shared_bus.open()
            self._scan_online_ids(self._shared_bus, serial_port)
            for index in range(STEER_JOINT_COUNT):
                self._init_channel(index, serial_port, servo_ids[index], self._shared_bus)
            if not self._channels:
                raise RuntimeError("Ningún servo de dirección disponible")
            self.get_logger().info(f"Modo bus único en {serial_port}")
            self._hold_all_servos()
        else:
            for index in range(STEER_JOINT_COUNT):
                bus = StsServoBus(serial_ports[index], baud_rate, protocol_end)
                bus.open()
                self._init_channel(index, serial_ports[index], servo_ids[index], bus)
            self.get_logger().info("Modo 4 drivers USB")
            self._hold_all_servos()

        self.create_subscription(Float64MultiArray, self.joint_commands_topic, self._on_commands, 10)
        self._state_pub = self.create_publisher(Float64MultiArray, self.steer_states_topic, 10)
        self.create_timer(1.0 / self.control_rate_hz, self._on_timer)
        self._ready = True

        self.get_logger().info(f"Escuchando {self.joint_commands_topic}")

    def _ping_servo(self, bus: StsServoBus, servo_id: int) -> bool:
        for attempt in range(max(1, self.ping_retries)):
            if bus.ping(servo_id):
                return True
            time.sleep(0.05)
        return False

    def _init_channel(
        self,
        index: int,
        port: str,
        servo_id: int,
        bus: StsServoBus,
    ) -> bool:
        if not self._ping_servo(bus, servo_id):
            msg = (
                f"{STEER_JOINT_NAMES[index]}: servo id={servo_id} no responde en {port}"
            )
            if self.require_all_servos:
                raise RuntimeError(msg)
            self.get_logger().warning(f"{msg} — omitido")
            return False

        bus.enable_torque(servo_id, True)
        self._channels.append(
            SteerChannel(
                name=STEER_JOINT_NAMES[index],
                port=port,
                servo_id=servo_id,
                joint_index=index,
                bus=bus,
            )
        )
        self.get_logger().info(
            f"{STEER_JOINT_NAMES[index]} (id={servo_id}): "
            f"cent={self._center_counts[index]} "
            f"+90={self._counts_plus_90[index]} "
            f"-90={self._counts_minus_90[index]}"
        )
        return True

    def _scan_online_ids(self, bus: StsServoBus, port: str) -> List[int]:
        online = []
        for sid in range(0, 21):
            if self._ping_servo(bus, sid):
                online.append(sid)
        if online:
            self.get_logger().info(f"IDs detectados en {port}: {online}")
        else:
            self.get_logger().warning(f"Ningún servo respondió en {port}")
        return online

    def _clamp_angle(self, angle_rad: float) -> float:
        limit = self.steering_angle_limit_rad
        return max(-limit, min(limit, angle_rad))

    def _angle_to_counts(self, angle_rad: float, joint_index: int) -> int:
        return calibrated_angle_to_counts(
            self._clamp_angle(angle_rad),
            self._center_counts[joint_index],
            self._counts_plus_90[joint_index],
            self._counts_minus_90[joint_index],
            self.steering_angle_limit_rad,
        )

    def _counts_to_angle(self, counts: int, joint_index: int) -> float:
        return calibrated_counts_to_rad(
            counts,
            self._center_counts[joint_index],
            self._counts_plus_90[joint_index],
            self._counts_minus_90[joint_index],
            self.steering_angle_limit_rad,
        )

    def _hold_all_servos(self) -> None:
        if not self._channels:
            return

        positions = [self._center_counts[ch.joint_index] for ch in self._channels]
        active_ids = [channel.servo_id for channel in self._channels]
        try:
            if self._use_single_bus and self._shared_bus is not None:
                self._shared_bus.sync_write_positions_timed(
                    active_ids,
                    positions,
                    self.move_time_ms,
                    self.move_acc,
                )
            else:
                for channel, position in zip(self._channels, positions):
                    channel.bus.write_position_timed(
                        channel.servo_id,
                        position,
                        self.move_time_ms,
                        self.move_acc,
                    )
            self.get_logger().info("Servos en posición de cero calibrada (centro)")
        except RuntimeError as exc:
            self.get_logger().error(f"No se pudo ir al centro calibrado: {exc}")

    def _on_commands(self, msg: Float64MultiArray) -> None:
        if len(msg.data) < STEER_JOINT_COUNT:
            return
        for index in range(STEER_JOINT_COUNT):
            self._target_angles[index] = self._clamp_angle(float(msg.data[index]))
        self._last_cmd_time = self.get_clock().now()

    def _on_timer(self) -> None:
        if not self._ready:
            return

        angles = [self._clamp_angle(a) for a in self._target_angles]
        if self._last_cmd_time is not None:
            age = (self.get_clock().now() - self._last_cmd_time).nanoseconds * 1e-9
            if age > self.command_timeout_sec:
                angles = [0.0] * STEER_JOINT_COUNT
        else:
            return

        positions = [
            self._angle_to_counts(angles[index], index)
            for index in range(STEER_JOINT_COUNT)
        ]

        active_ids = [channel.servo_id for channel in self._channels]
        active_positions = [positions[ch.joint_index] for ch in self._channels]

        state_msg = Float64MultiArray()
        state_msg.data = [0.0] * STEER_JOINT_COUNT

        try:
            if self._use_single_bus and self._shared_bus is not None:
                self._shared_bus.sync_write_positions_timed(
                    active_ids,
                    active_positions,
                    self.move_time_ms,
                    self.move_acc,
                )
            else:
                for channel in self._channels:
                    channel.bus.write_position_timed(
                        channel.servo_id,
                        positions[channel.joint_index],
                        self.move_time_ms,
                        self.move_acc,
                    )
        except RuntimeError as exc:
            self.get_logger().error(f"Servo write failed: {exc}")
            return

        for channel in self._channels:
            try:
                counts = channel.bus.read_position(channel.servo_id)
                angle = self._counts_to_angle(counts, channel.joint_index)
            except RuntimeError:
                angle = angles[channel.joint_index]
            state_msg.data[channel.joint_index] = angle

        self._state_pub.publish(state_msg)

    def destroy_node(self) -> bool:
        try:
            seen_buses = set()
            for channel in self._channels:
                channel.bus.enable_torque(channel.servo_id, False)
                bus_id = id(channel.bus)
                if bus_id not in seen_buses:
                    channel.bus.close()
                    seen_buses.add(bus_id)
        except Exception:
            pass
        return super().destroy_node()


def main() -> None:
    rclpy.init()
    node = SteerServoNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

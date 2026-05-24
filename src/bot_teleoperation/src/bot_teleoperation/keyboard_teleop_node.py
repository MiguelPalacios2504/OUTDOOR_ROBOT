#!/usr/bin/env python3
"""Holonomic keyboard teleop (4WIS): Twist on /cmd_vel with diagonal + yaw."""

from __future__ import annotations

import math
import select
import sys
import termios
import tty
from typing import Optional, TextIO, Tuple

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node

HELP = """
bot_teleoperation — teleop holonómico (4WIS / cmd_vel)
------------------------------------------------------
  Traslación (combinable = diagonal)     Giro Z (combinable con traslación)
    w  adelante (+X)                       q  o  z   giro antihorario (+ω)
    s  atrás (-X)                          e  o  c   giro horario (-ω)
    a  strafe izquierda (+Y)               [  /  ]   paso angular
    d  strafe derecha (-Y)

  Flechas: ↑↓ = X,  ←→ = Y   (misma lógica que WASD)

  Parar todo          x
  Deadman (mantener)  espacio   (si require_deadman=true)

  Paso lineal +/-     + / -     (incremental) o escala global (absolute)
  Modo teclas         t   alterna sticky / mantener pulsado (solo absolute)

  Incremental (default): cada pulsación suma/resta un paso (linear_step).
  Diagonal holonómico: w luego a acumula vx+vy. x para parar.

  Absolute: t alterna sticky/hold; una tecla = velocidad máxima en ese eje.

  Ctrl+C para salir.
"""

# Logical motion ids
FWD, BACK, LEFT, RIGHT, YAW_LEFT, YAW_RIGHT = (
    "fwd",
    "back",
    "left",
    "right",
    "yaw_left",
    "yaw_right",
)

TRANSLATION_GROUPS = (
    (FWD, BACK),
    (LEFT, RIGHT),
)
YAW_GROUP = (YAW_LEFT, YAW_RIGHT)

KEY_TO_MOTION = {
    "w": FWD,
    "s": BACK,
    "a": LEFT,
    "d": RIGHT,
    "q": YAW_LEFT,
    "e": YAW_RIGHT,
    "z": YAW_LEFT,
    "c": YAW_RIGHT,
    "up": FWD,
    "down": BACK,
    "left": LEFT,
    "right": RIGHT,
}


class KeyboardTeleopNode(Node):
    def __init__(self) -> None:
        super().__init__("keyboard_teleop_node")

        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("publish_rate_hz", 30.0)
        self.declare_parameter("max_linear_x", 0.5)
        self.declare_parameter("max_linear_y", 0.5)
        self.declare_parameter("max_angular_z", 1.0)
        self.declare_parameter("holonomic_normalize", True)
        self.declare_parameter("speed_step", 0.1)
        self.declare_parameter("control_mode", "incremental")
        self.declare_parameter("linear_step", 0.05)
        self.declare_parameter("angular_step", 0.1)
        self.declare_parameter("require_deadman", False)
        self.declare_parameter("sticky_keys", True)
        self.declare_parameter("key_timeout_s", 0.35)

        self.cmd_vel_topic = str(self.get_parameter("cmd_vel_topic").value)
        rate_hz = float(self.get_parameter("publish_rate_hz").value)
        self.max_linear_x = float(self.get_parameter("max_linear_x").value)
        self.max_linear_y = float(self.get_parameter("max_linear_y").value)
        self.max_angular_z = float(self.get_parameter("max_angular_z").value)
        self.holonomic_normalize = bool(self.get_parameter("holonomic_normalize").value)
        self.speed_step = float(self.get_parameter("speed_step").value)
        self.control_mode = str(self.get_parameter("control_mode").value).strip().lower()
        self.linear_step = float(self.get_parameter("linear_step").value)
        self.angular_step = float(self.get_parameter("angular_step").value)
        self.require_deadman = bool(self.get_parameter("require_deadman").value)
        self.sticky_keys = bool(self.get_parameter("sticky_keys").value)
        self.key_timeout_s = float(self.get_parameter("key_timeout_s").value)

        if self.control_mode not in ("incremental", "absolute"):
            raise ValueError("control_mode must be 'incremental' or 'absolute'")

        self.speed_scale = 1.0
        self.vx = 0.0
        self.vy = 0.0
        self.omega = 0.0
        self.active_motions: set[str] = set()
        self.deadman_pressed = False
        self._last_key_time = self.get_clock().now()

        self.publisher = self.create_publisher(Twist, self.cmd_vel_topic, 10)
        period = 1.0 / max(rate_hz, 1.0)
        self.timer = self.create_timer(period, self.publish_cmd_vel)

        if self.control_mode == "incremental":
            mode = "incremental"
        else:
            mode = "sticky" if self.sticky_keys else "hold"
        self.get_logger().info(
            "Holonomic teleop on %s [%s, deadman=%s]. Focus this terminal."
            % (self.cmd_vel_topic, mode, self.require_deadman)
        )

    def _clamp_velocities(self) -> None:
        scale = self.speed_scale
        self.vx = max(-self.max_linear_x * scale, min(self.max_linear_x * scale, self.vx))
        self.vy = max(-self.max_linear_y * scale, min(self.max_linear_y * scale, self.vy))
        self.omega = max(-self.max_angular_z * scale, min(self.max_angular_z * scale, self.omega))

    def _apply_holonomic_normalize(self, vx: float, vy: float) -> Tuple[float, float]:
        if not self.holonomic_normalize:
            return vx, vy
        mag = math.hypot(vx, vy)
        cap = max(self.max_linear_x, self.max_linear_y) * self.speed_scale
        if mag > cap and mag > 1e-9:
            factor = cap / mag
            return vx * factor, vy * factor
        return vx, vy

    def _absolute_twist(self) -> Tuple[float, float, float]:
        scale = self.speed_scale
        vx = vy = omega = 0.0

        if FWD in self.active_motions:
            vx += self.max_linear_x * scale
        if BACK in self.active_motions:
            vx -= self.max_linear_x * scale
        if LEFT in self.active_motions:
            vy += self.max_linear_y * scale
        if RIGHT in self.active_motions:
            vy -= self.max_linear_y * scale
        if YAW_LEFT in self.active_motions:
            omega += self.max_angular_z * scale
        if YAW_RIGHT in self.active_motions:
            omega -= self.max_angular_z * scale

        vx, vy = self._apply_holonomic_normalize(vx, vy)
        return vx, vy, omega

    def _incremental_delta(self, motion: str) -> Tuple[float, float, float]:
        scale = self.speed_scale
        dvx = dvy = domega = 0.0
        if motion == FWD:
            dvx = self.linear_step * scale
        elif motion == BACK:
            dvx = -self.linear_step * scale
        elif motion == LEFT:
            dvy = self.linear_step * scale
        elif motion == RIGHT:
            dvy = -self.linear_step * scale
        elif motion == YAW_LEFT:
            domega = self.angular_step * scale
        elif motion == YAW_RIGHT:
            domega = -self.angular_step * scale
        return dvx, dvy, domega

    def apply_incremental_motion(self, motion: str) -> None:
        dvx, dvy, domega = self._incremental_delta(motion)
        self.vx += dvx
        self.vy += dvy
        self.omega += domega
        self._clamp_velocities()
        self._log_twist_preview()

    def publish_cmd_vel(self) -> None:
        if self.control_mode == "absolute" and not self.sticky_keys:
            now = self.get_clock().now()
            elapsed = (now - self._last_key_time).nanoseconds * 1e-9
            if elapsed > self.key_timeout_s:
                self.active_motions.clear()
                if self.require_deadman:
                    self.deadman_pressed = False

        msg = Twist()
        if self.require_deadman and not self.deadman_pressed:
            self.publisher.publish(msg)
            return

        if self.control_mode == "incremental":
            vx, vy = self._apply_holonomic_normalize(self.vx, self.vy)
            omega = self.omega
        else:
            vx, vy, omega = self._absolute_twist()

        msg.linear.x = vx
        msg.linear.y = vy
        msg.angular.z = omega
        self.publisher.publish(msg)

    def _toggle_motion(self, motion: str) -> None:
        group = None
        for g in TRANSLATION_GROUPS + (YAW_GROUP,):
            if motion in g:
                group = g
                break
        if group is None:
            return
        if motion in self.active_motions:
            self.active_motions.discard(motion)
        else:
            for other in group:
                self.active_motions.discard(other)
            self.active_motions.add(motion)

    def _hold_motion(self, motion: str) -> None:
        for g in TRANSLATION_GROUPS + (YAW_GROUP,):
            if motion in g:
                for other in g:
                    if other != motion:
                        self.active_motions.discard(other)
                break
        self.active_motions.add(motion)

    def apply_motion_key(self, motion: str) -> None:
        if self.control_mode == "incremental":
            self.apply_incremental_motion(motion)
            return
        if self.sticky_keys:
            self._toggle_motion(motion)
        else:
            self._hold_motion(motion)
        self._log_twist_preview()

    def _log_twist_preview(self) -> None:
        if self.control_mode == "incremental":
            self.get_logger().info(
                "cmd_vel: vx=%.3f vy=%.3f wz=%.3f"
                % (self.vx, self.vy, self.omega)
            )
            return
        keys = sorted(self.active_motions)
        self.get_logger().info("active: %s" % (keys if keys else "(stop)"))

    def process_key(self, key: str) -> bool:
        self._last_key_time = self.get_clock().now()

        if key in ("\x03", "\x04"):
            return False

        if key == "+":
            if self.control_mode == "incremental":
                self.linear_step += self.speed_step
                self.angular_step += self.speed_step
                self.get_logger().info(
                    "step: linear=%.3f angular=%.3f" % (self.linear_step, self.angular_step)
                )
            else:
                self.speed_scale = min(1.0, self.speed_scale + self.speed_step)
                self.get_logger().info("speed scale: %.2f" % self.speed_scale)
            return True
        if key in ("-", "_"):
            if self.control_mode == "incremental":
                self.linear_step = max(0.01, self.linear_step - self.speed_step)
                self.angular_step = max(0.01, self.angular_step - self.speed_step)
                self.get_logger().info(
                    "step: linear=%.3f angular=%.3f" % (self.linear_step, self.angular_step)
                )
            else:
                self.speed_scale = max(0.1, self.speed_scale - self.speed_step)
                self.get_logger().info("speed scale: %.2f" % self.speed_scale)
            return True
        if key == "[":
            if self.control_mode == "incremental":
                self.angular_step = max(0.01, self.angular_step - self.speed_step)
                self.get_logger().info("angular step: %.3f rad/s" % self.angular_step)
            else:
                self.max_angular_z = max(0.1, self.max_angular_z - self.speed_step)
                self.get_logger().info("max angular.z: %.2f rad/s" % self.max_angular_z)
            return True
        if key == "]":
            if self.control_mode == "incremental":
                self.angular_step += self.speed_step
                self.get_logger().info("angular step: %.3f rad/s" % self.angular_step)
            else:
                self.max_angular_z += self.speed_step
                self.get_logger().info("max angular.z: %.2f rad/s" % self.max_angular_z)
            return True
        if key == "t":
            if self.control_mode == "incremental":
                self.get_logger().info("toggle t only applies in absolute mode")
                return True
            self.sticky_keys = not self.sticky_keys
            self.active_motions.clear()
            mode = "sticky" if self.sticky_keys else "hold"
            self.get_logger().info("key mode: %s" % mode)
            return True

        if key == " ":
            self.deadman_pressed = True
            return True

        if key == "x":
            self.active_motions.clear()
            self.deadman_pressed = False
            self.vx = 0.0
            self.vy = 0.0
            self.omega = 0.0
            self.publish_stop()
            return True

        motion = KEY_TO_MOTION.get(key)
        if motion is not None:
            self.apply_motion_key(motion)
            return True

        return True

    def publish_stop(self) -> None:
        self.active_motions.clear()
        self.deadman_pressed = False
        self.vx = 0.0
        self.vy = 0.0
        self.omega = 0.0
        self.publisher.publish(Twist())


def _read_key(stream: TextIO) -> Optional[str]:
    """Read one key or arrow escape sequence."""
    key = stream.read(1)
    if not key:
        return None
    if key != "\x1b":
        return key
    if not select.select([stream], [], [], 0.02)[0]:
        return key
    seq = stream.read(2)
    if seq == "[A":
        return "up"
    if seq == "[B":
        return "down"
    if seq == "[C":
        return "right"
    if seq == "[D":
        return "left"
    return key


def _open_keyboard_stream() -> Tuple[TextIO, list, bool]:
    stream: TextIO = sys.stdin
    opened_dev_tty = False
    if not stream.isatty():
        try:
            stream = open("/dev/tty", "r", encoding="utf-8", errors="replace")
            opened_dev_tty = True
        except OSError as exc:
            raise SystemExit(
                "Keyboard teleop needs an interactive terminal (TTY).\n"
                "  • Run in a normal terminal (not only the IDE output panel).\n"
                "  • Or: ros2 run bot_teleoperation keyboard_teleop_node\n"
                "  • Launch uses emulate_tty; if it still fails, use ros2 run."
            ) from exc
    try:
        settings = termios.tcgetattr(stream)
    except termios.error as exc:
        raise SystemExit(
            "Cannot configure terminal for keyboard input (%s).\n"
            "Use a real TTY: ros2 run bot_teleoperation keyboard_teleop_node"
            % exc
        ) from exc
    return stream, settings, opened_dev_tty


def main(args: Optional[list[str]] = None) -> None:
    print(HELP)
    stream, settings, opened_dev_tty = _open_keyboard_stream()
    fd = stream.fileno()

    rclpy.init(args=args)
    node = KeyboardTeleopNode()
    running = True

    try:
        while rclpy.ok() and running:
            rclpy.spin_once(node, timeout_sec=0.0)
            tty.setraw(fd)
            try:
                ready, _, _ = select.select([stream], [], [], 0.05)
                if ready:
                    key = _read_key(stream)
                    if key:
                        running = node.process_key(key)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, settings)
    except KeyboardInterrupt:
        pass
    finally:
        node.publish_stop()
        node.destroy_node()
        rclpy.shutdown()
        if opened_dev_tty:
            stream.close()


if __name__ == "__main__":
    main()

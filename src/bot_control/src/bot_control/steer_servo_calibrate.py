#!/usr/bin/env python3
"""Calibración manual de servos de dirección (estilo brazo LeRobot).

Modos:
  explore    — torque OFF en todos; mueve a mano y ve posiciones en vivo
  calibrate  — un servo a la vez; registra neutral al inicio y min/max por rueda

Uso:
  ros2 run bot_control steer_servo_calibrate -- explore
  ros2 run bot_control steer_servo_calibrate -- calibrate
"""

from __future__ import annotations

import argparse
import select
import sys
import termios
import time
import tty
from dataclasses import dataclass
from typing import List, Sequence

from bot_control.sts_servo_bus import StsServoBus

DEFAULT_PORT = "/dev/ttyACM0"
DEFAULT_BAUD = 1_000_000
DEFAULT_PROTOCOL = 1
DEFAULT_NAMES = ("FL", "FR", "BL", "BR")
DEFAULT_IDS = (11, 14, 12, 13)
DEFAULT_JOINTS = ("f_left_steer", "f_right_steer", "b_leftsteer", "b_rightsteer")


@dataclass
class ServoCal:
    name: str
    joint: str
    servo_id: int
    pos_min: int
    pos_max: int
    center: int  # posición recta registrada al inicio (no el punto medio min/max)

    @property
    def span(self) -> int:
        return self.pos_max - self.pos_min


def _wait_enter(prompt: str) -> None:
    input(prompt)


def _stdin_ready() -> bool:
    return bool(select.select([sys.stdin], [], [], 0.0)[0])


def _read_position_safe(bus: StsServoBus, servo_id: int) -> int | None:
    try:
        return bus.read_position(servo_id)
    except RuntimeError:
        return None


def _set_all_torque(bus: StsServoBus, ids: Sequence[int], enable: bool) -> None:
    for servo_id in ids:
        bus.enable_torque(servo_id, enable)


def run_explore(bus: StsServoBus, names: Sequence[str], ids: Sequence[int]) -> None:
    print("\n=== MODO EXPLORE ===")
    print("Torque DESACTIVADO en todos los servos.")
    print("Mueve las ruedas a mano. Pulsa ENTER para terminar.\n")

    _set_all_torque(bus, ids, False)

    labels = [f"{n}(id={i})" for n, i in zip(names, ids)]
    try:
        while True:
            if _stdin_ready():
                sys.stdin.readline()
                break

            parts = []
            for label, servo_id in zip(labels, ids):
                pos = _read_position_safe(bus, servo_id)
                parts.append(f"{label}={pos if pos is not None else '?'}")

            line = "  |  ".join(parts)
            print(f"\r{line:<90}", end="", flush=True)
            time.sleep(0.08)
    finally:
        print("\n\nFin explore. Reactivando torque...")
        _set_all_torque(bus, ids, True)


def _record_range(bus: StsServoBus, servo_id: int) -> tuple[int, int, int]:
    pos_min = 4095
    pos_max = 0
    samples = 0

    while True:
        if _stdin_ready():
            sys.stdin.readline()
            break

        pos = _read_position_safe(bus, servo_id)
        if pos is not None:
            pos_min = min(pos_min, pos)
            pos_max = max(pos_max, pos)
            samples += 1
            midpoint = int(round(0.5 * (pos_min + pos_max)))
            print(
                f"\r  ticks={pos:4d}  min={pos_min:4d}  max={pos_max:4d}  "
                f"mid={midpoint:4d}  muestras={samples}   (ENTER=siguiente)",
                end="",
                flush=True,
            )
        time.sleep(0.06)

    if samples == 0:
        raise RuntimeError("No se leyó ninguna posición")

    print()
    return pos_min, pos_max, samples


def run_calibrate(bus: StsServoBus, names: Sequence[str], joints: Sequence[str], ids: Sequence[int]) -> List[ServoCal]:
    print("\n=== CALIBRACIÓN MANUAL (un servo a la vez) ===")
    print("Para cada rueda:")
    print("  1. Torque OFF solo en ese servo")
    print("  2. Muévelo a mano hasta los topes seguros (sin chocar chasis)")
    print("  3. Pulsa ENTER para guardar min/max")
    print("El centro (0°) es la posición recta del paso inicial, no el punto medio del rango.\n")

    _wait_enter("Coloca TODAS las ruedas en posición recta/neutral y pulsa ENTER...")

    neutral_counts: List[int] = []
    print("\nPosición recta registrada:")
    for name, servo_id in zip(names, ids):
        pos = _read_position_safe(bus, servo_id)
        if pos is None:
            raise RuntimeError(f"No se pudo leer posición neutral de {name} (id={servo_id})")
        neutral_counts.append(pos)
        print(f"  {name} id={servo_id}: neutral={pos}")

    results: List[ServoCal] = []

    for index, (name, joint, servo_id) in enumerate(zip(names, joints, ids)):
        print(f"\n--- [{index + 1}/{len(ids)}] {name}  joint={joint}  id={servo_id} ---")
        _set_all_torque(bus, ids, True)
        bus.enable_torque(servo_id, False)
        print("  Torque OFF. Mueve SOLO esta rueda por todo su rango seguro.")

        pos_min, pos_max, _ = _record_range(bus, servo_id)
        bus.enable_torque(servo_id, True)

        cal = ServoCal(
            name=name,
            joint=joint,
            servo_id=servo_id,
            pos_min=pos_min,
            pos_max=pos_max,
            center=neutral_counts[index],
        )
        results.append(cal)
        midpoint = int(round(0.5 * (pos_min + pos_max)))
        print(
            f"  OK {name}: min={cal.pos_min} max={cal.pos_max} "
            f"centro={cal.center} (mid={midpoint}) span={cal.span}"
        )

    return results


def _print_yaml(results: Sequence[ServoCal], limit_deg: float) -> None:
    centers = [r.center for r in results]
    plus = [r.pos_max for r in results]
    minus = [r.pos_min for r in results]
    ids = [r.servo_id for r in results]

    print("\n" + "=" * 60)
    print("Copia esto en steer_servo.yaml:")
    print("=" * 60)
    print("    servo_ids: [%s]" % ", ".join(str(i) for i in ids))
    print("    center_counts: [%s]" % ", ".join(str(c) for c in centers))
    print("    counts_plus_90: [%s]   # max registrado" % ", ".join(str(c) for c in plus))
    print("    counts_minus_90: [%s]  # min registrado" % ", ".join(str(c) for c in minus))
    print("    steering_angle_limit_deg: %.1f" % limit_deg)
    print()
    for r in results:
        print(
            f"  # {r.name} id={r.servo_id}: cent={r.center} "
            f"+lim={r.pos_max} -lim={r.pos_min}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibración manual servos dirección")
    parser.add_argument(
        "mode",
        nargs="?",
        choices=("explore", "calibrate"),
        default="explore",
        help="explore=ver posiciones; calibrate=registrar rangos",
    )
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument("--protocol", type=int, default=DEFAULT_PROTOCOL)
    parser.add_argument("--ids", default=",".join(str(i) for i in DEFAULT_IDS))
    parser.add_argument("--names", default=",".join(DEFAULT_NAMES))
    parser.add_argument("--limit-deg", type=float, default=45.0)
    args = parser.parse_args()

    ids = [int(x.strip()) for x in args.ids.split(",") if x.strip()]
    names = [x.strip() for x in args.names.split(",") if x.strip()]
    joints = list(DEFAULT_JOINTS[: len(ids)])

    if len(ids) != len(names):
        raise SystemExit("ids y names deben tener la misma cantidad")

    bus = StsServoBus(args.port, args.baud, args.protocol)
    bus.open()

    print(f"Puerto {args.port} @ {args.baud}  protocol_end={args.protocol}")
    for name, servo_id in zip(names, ids):
        if not bus.ping(servo_id):
            raise SystemExit(f"Servo id={servo_id} ({name}) no responde")

    old_tty = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        if args.mode == "explore":
            run_explore(bus, names, ids)
        else:
            results = run_calibrate(bus, names, joints, ids)
            _print_yaml(results, args.limit_deg)
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
        try:
            _set_all_torque(bus, ids, True)
        except Exception:
            pass
        bus.close()


if __name__ == "__main__":
    main()

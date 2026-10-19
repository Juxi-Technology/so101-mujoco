"""Read-only hardware check for an SO-ARM101 arm on a serial port.

Pings the six STS3215 servos, then reads each joint's raw position, supply
voltage, temperature and torque-enable state. Performs NO writes of any kind
and leaves the torque state exactly as found, so it is safe as the very first
contact with a freshly wired arm (before calibration).

Usage (from the repo root):

    uv run --frozen python examples/so101_mujoco/hardware_check.py --port COM163
"""

from __future__ import annotations

import argparse
import sys

from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus

MOTORS = {
    "shoulder_pan": Motor(1, "sts3215", MotorNormMode.RANGE_M100_100),
    "shoulder_lift": Motor(2, "sts3215", MotorNormMode.RANGE_M100_100),
    "elbow_flex": Motor(3, "sts3215", MotorNormMode.RANGE_M100_100),
    "wrist_flex": Motor(4, "sts3215", MotorNormMode.RANGE_M100_100),
    "wrist_roll": Motor(5, "sts3215", MotorNormMode.RANGE_M100_100),
    "gripper": Motor(6, "sts3215", MotorNormMode.RANGE_0_100),
}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--port", required=True, help="serial port, e.g. COM163")
    args = p.parse_args()

    bus = FeetechMotorsBus(port=args.port, motors=MOTORS, calibration={})
    try:
        bus.connect()  # handshake: pings ids 1-6 and checks firmware consistency
    except Exception as e:  # noqa: BLE001
        print(f"connect failed on {args.port}: {e}", file=sys.stderr)
        return 1

    try:
        pos = bus.sync_read("Present_Position", normalize=False)
        torque = bus.sync_read("Torque_Enable", normalize=False)
        volt = bus.sync_read("Present_Voltage", normalize=False)
        temp = bus.sync_read("Present_Temperature", normalize=False)
        print(f"{'joint':14s} {'id':>2s} {'pos(raw)':>8s} {'deg*':>7s} {'torque':>6s} {'volt':>6s} {'temp':>5s}")
        for name, motor in MOTORS.items():
            deg = (pos[name] - 2048) * 360.0 / 4096.0  # raw counts -> approx degrees
            print(
                f"{name:14s} {motor.id:2d} {pos[name]:8d} {deg:+7.1f} "
                f"{str(torque[name]):>6s} {volt[name] / 10:.1f}V {temp[name]:4d}C"
            )
    finally:
        bus.disconnect(disable_torque=False)  # leave torque exactly as found
    print("read-only check done; nothing was written to the servos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

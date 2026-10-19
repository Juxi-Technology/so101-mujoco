"""Run ``lerobot-teleoperate`` with the SO-ARM101 MuJoCo robot + keyboard teleop.

All official ``lerobot-teleoperate`` flags apply; ``--robot.type`` and
``--teleop.type`` default to ``so101_mujoco`` / ``so101_keyboard``.

Usage (from the repo root):

    uv run --with mujoco python examples/so101_mujoco/teleoperate.py
    uv run --with mujoco python examples/so101_mujoco/teleoperate.py --fps=30

Hold w/s a/z e/d t/g y/h u/j to move the joints (see the teleop module for the
mapping). The MuJoCo viewer window shows the arm; keys work while it is focused.
"""

from __future__ import annotations

import sys

# Importing these modules registers the `so101_mujoco` robot and the
# `so101_keyboard` / `so101_leader_trim` teleoperators in the LeRobot registries.
import so101_keyboard_teleop  # noqa: F401
import so101_leader_trim  # noqa: F401
import so101_mujoco_robot  # noqa: F401
from so101_keyboard_teleop import drain_pending_keys


def _with_defaults(argv: list[str]) -> list[str]:
    if not any(a.split("=", 1)[0] == "--robot.type" for a in argv):
        argv = [*argv, "--robot.type=so101_mujoco"]
    if not any(a.split("=", 1)[0] == "--teleop.type" for a in argv):
        argv = [*argv, "--teleop.type=so101_keyboard"]
    return argv


if __name__ == "__main__":
    sys.argv = _with_defaults(sys.argv)
    from lerobot.scripts.lerobot_teleoperate import main
    from lerobot.utils.errors import DeviceNotConnectedError

    try:
        main()
    except DeviceNotConnectedError:
        # Pressing Esc in the keyboard teleoperator disconnects it mid-session;
        # end the run with a clear message instead of a traceback.
        print("\nSession ended: a device was disconnected (Esc pressed or unplugged).")
    finally:
        drain_pending_keys()

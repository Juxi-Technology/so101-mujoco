"""Run ``lerobot-replay`` with the SO-ARM101 MuJoCo robot registered.

The official ``lerobot-replay`` entry point does not import this repository's
plugin modules, so ``--robot.type=so101_mujoco`` is not a valid choice there.
This launcher registers the plugins first (robot default: ``so101_mujoco``) and
then hands over to the official script.

Usage (from the repo root):

    uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
        --dataset.repo_id=local/so101_sim_teleop \
        --dataset.root=examples/so101_mujoco/outputs/datasets/sim_run2 \
        --dataset.episode=1

Replays the recorded action trajectory on the simulated follower (MuJoCo window
opens automatically). Works with ``--robot.type=so101_follower`` too, to replay
on the real arm.
"""

from __future__ import annotations

import sys

# Importing these modules registers the `so101_mujoco` robot (and the keyboard /
# leader teleoperators, harmless here) in the LeRobot registries.
import so101_keyboard_teleop  # noqa: F401
import so101_leader_trim  # noqa: F401
import so101_mujoco_robot  # noqa: F401


def _with_defaults(argv: list[str]) -> list[str]:
    if not any(a.split("=", 1)[0] == "--robot.type" for a in argv):
        argv = [*argv, "--robot.type=so101_mujoco"]
    return argv


if __name__ == "__main__":
    sys.argv = _with_defaults(sys.argv)
    from lerobot.scripts.lerobot_replay import main

    main()

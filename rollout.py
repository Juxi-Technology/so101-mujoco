"""Run ``lerobot-rollout`` with the SO-ARM101 MuJoCo robot registered.

The official ``lerobot-rollout`` entry point does not import this repository's
plugin modules, so ``--robot.type=so101_mujoco`` is not a valid choice there.
This launcher registers the plugins first (robot default: ``so101_mujoco``)
and then hands over to the official script.

Usage (from the repo root) -- deploy a trained policy in the sim:

    uv run --frozen --with mujoco python examples/so101_mujoco/rollout.py \
        --policy.path=examples/so101_mujoco/outputs/train/act_so101/checkpoints/last/pretrained_model \
        --strategy.type=base \
        --robot.image_camera=sim_cam --robot.top_camera=top_cam \
        --task="put the cube in the box" --duration=30

Notes:
* ``--robot.image_camera/--robot.top_camera`` must match how the dataset was
  recorded, otherwise the policy gets no camera observations.
* ``--task`` is the natural-language task string (same as the recording's
  ``--dataset.single_task``).
* ``--strategy.type=base`` is a plain autonomous rollout for ``--duration``
  seconds; see ``lerobot-rollout --help`` for recording strategies (sentry,
  highlight, dagger, episodic).
* Works with ``--robot.type=so101_follower`` too, to deploy on the real arm
  (add ``--robot.port=... --robot.id=... --robot.use_degrees=false``).
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
    from lerobot.scripts.lerobot_rollout import main

    main()

"""Run ``lerobot-record`` with the SO-ARM101 MuJoCo robot + keyboard teleop.

All official ``lerobot-record`` flags apply; ``--robot.type`` and
``--teleop.type`` default to ``so101_mujoco`` / ``so101_keyboard``.

Usage (from the repo root):

    uv run --with mujoco python examples/so101_mujoco/record.py \
        --dataset.repo_id=local/so101_mujoco_pick \
        --dataset.root=examples/so101_mujoco/outputs/datasets/run1 \
        --dataset.num_episodes=3 --dataset.episode_time_s=30 --dataset.reset_time_s=10 \
        --dataset.single_task="pick up the cube" \
        --dataset.video=false --dataset.push_to_hub=false --play_sounds=false

Note: ``--dataset.root`` *is* the dataset directory (not a parent directory
that gets ``repo_id`` appended); use a fresh path per recording run.

Recording keys (handled by lerobot-record, global, same as on hardware):

    Right arrow / n : end the current episode early (save it)
    Left arrow  / r : discard and re-record the current episode
    q               : stop recording and finalize the dataset
    Esc             : same as q, but it also disconnects the keyboard teleop;
                      prefer q so the in-progress episode is saved cleanly

Teleop keys (hold to move): w/s shoulder_lift, a/z shoulder_pan, e/d elbow_flex,
t/g wrist_flex, y/h wrist_roll, u/j gripper. The MuJoCo viewer window shows the
arm; keys work while it is focused.

Sim scene reset: on hardware, "Reset the environment" is a human putting the
objects back between episodes. In the sim there is nobody to reach in, so this
launcher hooks that phase and teleports the task cubes back to their spawn
poses automatically -- after pressing -> you only need to drive the leader arm
back to its start pose; the cubes reset themselves. Hardware robots are
untouched (they don't have ``reset_scene_objects``).
"""

from __future__ import annotations

import os
import sys
import time

# Importing these modules registers the `so101_mujoco` robot and the
# `so101_keyboard` / `so101_leader_trim` teleoperators in the LeRobot registries.
import so101_keyboard_teleop  # noqa: F401
import so101_leader_trim  # noqa: F401
import so101_mujoco_robot  # noqa: F401
from so101_keyboard_teleop import drain_pending_keys


def _encode_video_worker_with_retry(*args, **kwargs):
    """Encode one video stream, retrying once after a short pause on failure.

    A transient allocation failure at encoder init (e.g. x264 failing to
    malloc under system memory-commit pressure) aborts ``save_episode`` and
    loses the whole episode. The one retry runs seconds later, usually after
    the sibling stream's encoder has already exited and freed its memory.
    """
    import lerobot.datasets.dataset_writer as dataset_writer

    _quiet_codec_logs()  # re-assert inside the worker, right before encoding
    try:
        return dataset_writer._encode_video_worker_original(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 -- retried once, then re-raised
        print(f"[record.py] video encode failed ({exc}); retrying once in 3 s ...", flush=True)
        time.sleep(3.0)
        return dataset_writer._encode_video_worker_original(*args, **kwargs)


def _install_encoder_retry() -> None:
    """Patch the video-encode worker; must also be active inside the workers.

    Runs at module import time on purpose: multiprocessing spawn re-imports
    this ``__main__`` module in every encoding worker, and that is where the
    patch has to be live -- the worker unpickles the *patched* function and
    resolves ``_encode_video_worker_original`` set up here.
    """
    import lerobot.datasets.dataset_writer as dataset_writer

    if getattr(dataset_writer, "_encode_video_worker", None) is _encode_video_worker_with_retry:
        return
    dataset_writer._encode_video_worker_original = dataset_writer._encode_video_worker
    dataset_writer._encode_video_worker = _encode_video_worker_with_retry


def _quiet_codec_logs() -> None:
    """Silence per-save encoder chatter (libx264 stats blocks flood the tab).

    Covers both pyav logging routes -- the native libav echo
    (``set_libav_level``) and the Python logging bridge (``set_level``) -- plus
    the HF ``datasets`` "Map:" progress bar. Applied in this process and in
    every spawn'd encoder worker (each imports this module before encoding);
    real errors still surface.
    """
    os.environ.setdefault("TQDM_DISABLE", "1")
    os.environ.setdefault("HF_DATASETS_DISABLE_PROGRESS_BARS", "1")
    try:
        import av

        if hasattr(av.logging, "set_libav_level"):
            av.logging.set_libav_level(av.logging.ERROR)
        av.logging.set_level(av.logging.ERROR)
    except Exception:  # noqa: BLE001 -- pyav absent only matters once datasets load
        pass


# Applied in this process *and* in every spawn'd encoder worker (each imports
# this module before unpickling its task).
_quiet_codec_logs()
_install_encoder_retry()


def _install_scene_reset_hook() -> None:
    """Patch ``record_loop`` for two sim-session guards.

    1. Auto-reset the sim scene during lerobot-record's reset phase.
       ``lerobot-record`` runs one unrecorded ``record_loop`` between episodes
       (the "Reset the environment" phase; it is the only call made *without* a
       dataset). On hardware a human re-arranges the objects during it; the sim
       robot cannot be reached into, so at the start of that phase we trigger
       ``robot.reset_scene_objects()`` instead (no-op for robots that lack it,
       e.g. real followers).

    2. Drop keyboard-control flags left over from *outside* a running episode.
       The control keys set shared flags that ``record_loop`` consumes at its
       first tick, so a ``->``/``<-`` pressed during the reset phase or the
       minute-long video encoding between episodes would be consumed by the
       *next* episode's first tick: ``->`` saves a 0-frame episode (which
       crashes ``save_episode``) and ``<-`` silently discards the fresh episode.
       Clearing the flags as each episode starts makes such stray presses no-ops;
       presses made while an episode really runs still take effect.
    """
    import lerobot.scripts.lerobot_record as lerobot_record

    original_record_loop = lerobot_record.record_loop

    def record_loop(*args, **kwargs):
        robot = kwargs.get("robot")
        events = kwargs.get("events")
        if kwargs.get("dataset") is None:
            if hasattr(robot, "reset_scene_objects"):
                robot.reset_scene_objects()
        elif events is not None:
            events["exit_early"] = False
            events["rerecord_episode"] = False
        result = original_record_loop(*args, **kwargs)
        if (
            kwargs.get("dataset") is None
            and events is not None
            and not events.get("rerecord_episode")
            and not events.get("stop_recording")
        ):
            # The save + dual-stream video encode that follow this phase print
            # nothing for up to a minute; announce it so nobody presses -> into
            # the void (guard 2 would silently drop the press anyway).
            print(
                "[record.py] reset done; saving the episode + encoding videos now "
                "(can take a minute -- keys are ignored until the next "
                "'Recording episode' line)",
                flush=True,
            )
        return result

    lerobot_record.record_loop = record_loop


def _with_defaults(argv: list[str]) -> list[str]:
    if not any(a.split("=", 1)[0] == "--robot.type" for a in argv):
        argv = [*argv, "--robot.type=so101_mujoco"]
    if not any(a.split("=", 1)[0] == "--teleop.type" for a in argv):
        argv = [*argv, "--teleop.type=so101_keyboard"]
    if not any(a.split("=", 1)[0] == "--dataset.rgb_encoder.vcodec" for a in argv):
        # The upstream default libsvtav1 fails a native allocation on this machine
        # when both camera encoders open at once (SvtMalloc OOM kills the whole
        # session inside save_episode); libx264 is far lighter. Pass an explicit
        # --dataset.rgb_encoder.vcodec to override.
        argv = [*argv, "--dataset.rgb_encoder.vcodec=h264"]
        print("[record.py] video codec defaulted to h264 (libsvtav1 OOMs here); "
              "override with --dataset.rgb_encoder.vcodec=...")
    if not any(a.split("=", 1)[0] == "--dataset.encoder_threads" for a in argv):
        # libx264 otherwise uses ~all cores per stream; the two camera streams
        # opening at once starve the 50 Hz sim rendering while an episode saves
        # (visible as viewer stutter). Two threads per stream stays smooth.
        argv = [*argv, "--dataset.encoder_threads=2"]
        print("[record.py] encoder threads capped at 2 (smoother sim while saving); "
              "override with --dataset.encoder_threads=...")
    return argv


if __name__ == "__main__":
    sys.argv = _with_defaults(sys.argv)
    _install_scene_reset_hook()
    from lerobot.scripts.lerobot_record import main
    from lerobot.utils.errors import DeviceNotConnectedError

    try:
        main()
    except DeviceNotConnectedError:
        # Esc in the keyboard teleoperator disconnects it mid-session; end with
        # a clear message instead of a traceback. Prefer `q` to stop recording
        # gracefully (it does not touch the teleoperator).
        print("\nSession ended: a device was disconnected (Esc pressed or unplugged).")
    finally:
        drain_pending_keys()

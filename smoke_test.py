"""Automated smoke test for the SO-ARM101 MuJoCo teleop/record stack.

Runs without a display and without real key presses:

  1. robot connects (headless), starts at the range-center pose;
  2. ``send_action`` tracking: a target is reached within tolerance;
  3. teleop integration: injected key events move the right joints at the set rate;
  4. mini recording: ``record_loop`` writes a short state-only episode into a
     LeRobotDataset, then the dataset is reloaded and its frames are checked.

Usage (from the repo root):

    uv run --with mujoco python examples/so101_mujoco/smoke_test.py
"""

from __future__ import annotations

import shutil
import tempfile
import threading
import time
from pathlib import Path

from lerobot.configs.dataset import DatasetRecordConfig
from lerobot.datasets import (
    LeRobotDataset,
    VideoEncodingManager,
    aggregate_pipeline_dataset_features,
    create_initial_features,
)
from lerobot.processor import make_default_processors
from lerobot.scripts.lerobot_record import record_loop
from lerobot.utils.feature_utils import combine_feature_dicts

from so101_keyboard_teleop import SO101KeyboardTeleop, SO101KeyboardTeleopConfig
from so101_mujoco_robot import JOINT_NAMES, SO101MujocoRobot, SO101MujocoRobotConfig

FPS = 30


def check(label: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}{(' -- ' + detail) if detail else ''}")
    if not ok:
        raise SystemExit(1)


def main() -> None:
    print("[1] robot connect (headless)")
    robot = SO101MujocoRobot(SO101MujocoRobotConfig(onscreen=False))
    robot.connect()
    obs = robot.get_observation()
    print("      " + " ".join(f"{k.split('.')[0]}={v:+.1f}" for k, v in obs.items()))
    # 0.5 unit tolerance: the sim thread has already stepped a few times before this
    # read (gravity/coupling drift at kp 998 is tiny but scheduling-dependent, so an
    # exact-zero check is flaky; a wrong start pose would be off by tens of units).
    check("starts at range centers (body ~0, gripper ~50)",
          all(abs(v) < 0.5 for k, v in obs.items() if k != "gripper.pos") and abs(obs["gripper.pos"] - 50) < 0.5,
          "obs=" + str({k.split(".")[0]: round(v, 2) for k, v in obs.items()}))

    print("[2] send_action tracking")
    goal = dict(obs)
    goal["shoulder_lift.pos"] = 30.0
    goal["gripper.pos"] = 20.0
    robot.send_action(goal)
    time.sleep(1.5)
    obs2 = robot.get_observation()
    check("shoulder_lift reached 30", abs(obs2["shoulder_lift.pos"] - 30.0) < 2.0, f"got {obs2['shoulder_lift.pos']:.2f}")
    check("gripper reached 20", abs(obs2["gripper.pos"] - 20.0) < 2.0, f"got {obs2['gripper.pos']:.2f}")
    sent = robot.send_action({"shoulder_pan.pos": 1e9})
    check("out-of-range target is clipped", abs(sent["shoulder_pan.pos"] - 100.0) < 1e-6)

    print("[3] keyboard teleop integration (injected events)")
    teleop = SO101KeyboardTeleop(SO101KeyboardTeleopConfig(rate=100.0, gripper_rate=100.0))
    teleop.connect()
    if teleop.listener is not None:
        # The listener is a *global* (non-consuming) hook: a human typing anywhere
        # on this machine sends real key events that would race the injected ones.
        # Stop it for the test; injected events go through the same queue.
        teleop.listener.stop()
        teleop.listener = None
    a0 = teleop.get_action()
    teleop._on_press("a")  # shoulder_pan +
    time.sleep(0.3)
    a1 = teleop.get_action()
    check("'a' moves shoulder_pan up", a1["shoulder_pan.pos"] > a0["shoulder_pan.pos"] + 5.0,
          f"{a0['shoulder_pan.pos']:.1f} -> {a1['shoulder_pan.pos']:.1f}")
    check("other joints stay put", abs(a1["elbow_flex.pos"] - a0["elbow_flex.pos"]) < 1e-9)
    teleop._on_release("a")
    teleop._on_press("j")  # gripper close
    time.sleep(0.2)
    a2 = teleop.get_action()
    check("'j' closes gripper", a2["gripper.pos"] < 50.0, f"gripper={a2['gripper.pos']:.1f}")
    teleop._on_release("j")
    teleop.disconnect()
    robot.disconnect()

    print("[4] mini recording -> LeRobotDataset")
    root = Path(tempfile.gettempdir()) / "so101_mujoco_smoke_ds"
    shutil.rmtree(root, ignore_errors=True)
    repo_id = "local/so101_mujoco_smoke"

    robot2 = SO101MujocoRobot(SO101MujocoRobotConfig(onscreen=False))
    teleop2 = SO101KeyboardTeleop(SO101KeyboardTeleopConfig(rate=60.0, gripper_rate=100.0))
    t_act, t_rob, t_obs = make_default_processors()
    features = combine_feature_dicts(
        aggregate_pipeline_dataset_features(
            pipeline=t_act, initial_features=create_initial_features(action=robot2.action_features), use_videos=False),
        aggregate_pipeline_dataset_features(
            pipeline=t_obs, initial_features=create_initial_features(observation=robot2.observation_features), use_videos=False),
    )
    robot2.connect()
    teleop2.connect()
    if teleop2.listener is not None:
        teleop2.listener.stop()  # see [3]: isolate from real key events while testing
        teleop2.listener = None
    dataset = LeRobotDataset.create(
        repo_id, FPS, root=root, robot_type=robot2.name, features=features, use_videos=False)

    def inject() -> None:
        time.sleep(0.4)
        # 's' swings shoulder_lift *up* (the free direction); 'w' down would
        # press the gripper into the floor and the contact would block it.
        teleop2._on_press("s")
        time.sleep(1.0)
        teleop2._on_release("s")
        time.sleep(0.3)
        teleop2._on_press("u")  # gripper open
        time.sleep(0.6)
        teleop2._on_release("u")

    injector = threading.Thread(target=inject, daemon=True)
    injector.start()
    try:
        with VideoEncodingManager(dataset):
            record_loop(
                robot=robot2,
                events={"exit_early": False},
                fps=FPS,
                teleop_action_processor=t_act,
                robot_action_processor=t_rob,
                robot_observation_processor=t_obs,
                teleop=teleop2,
                dataset=dataset,
                control_time_s=4.0,
                single_task="so101 mujoco smoke",
            )
            # save_episode() must run inside the manager: its __exit__ finalizes
            # the dataset writer (same pattern as lerobot-record).
            dataset.save_episode()
    finally:
        dataset.finalize()
        robot2.disconnect()
        teleop2.disconnect()
    injector.join(timeout=1.0)

    reloaded = LeRobotDataset(repo_id, root=root)
    n = len(reloaded)
    check("dataset has ~120 frames", n >= 110, f"frames={n}")
    # Frames carry packed vectors; JOINT_NAMES gives the column order.
    lift_col = JOINT_NAMES.index("shoulder_lift")
    grip_col = JOINT_NAMES.index("gripper")
    first, mid, last = reloaded[0], reloaded[n // 2], reloaded[n - 1]
    lift0, lift_mid = float(first["action"][lift_col]), float(mid["action"][lift_col])
    grip_last = float(last["action"][grip_col])
    check("shoulder_lift action moved during episode", lift_mid < lift0 - 20.0, f"{lift0:.1f} -> {lift_mid:.1f}")
    check("gripper action opened", grip_last > 55.0, f"gripper={grip_last:.1f}")
    check("observation tracks action",
          abs(float(last["observation.state"][lift_col]) - float(last["action"][lift_col])) < 3.0)
    print(f"      dataset: {root}  ({n} frames, task={first.get('task')})")

    print("[5] sim camera -> image observations (video dataset)")
    import numpy as np

    robot3 = SO101MujocoRobot(SO101MujocoRobotConfig(onscreen=False, image_camera="sim_cam"))
    robot3.connect()
    # No warm-up sleep: connect() itself waits until the first camera frame.
    obs3 = robot3.get_observation()
    check("image observation present", "wrist" in obs3)
    img = obs3.get("wrist")
    check("image frame uint8 (480, 640, 3)",
          img is not None and img.dtype == np.uint8 and img.shape == (480, 640, 3),
          f"got {None if img is None else (img.dtype, img.shape)}")
    check("image not blank", img is not None and float(img.std()) > 2.0,
          f"std={0.0 if img is None else float(img.std()):.1f}")

    root3 = Path(tempfile.gettempdir()) / "so101_mujoco_smoke_vision_ds"
    shutil.rmtree(root3, ignore_errors=True)
    teleop3 = SO101KeyboardTeleop(SO101KeyboardTeleopConfig(rate=60.0, gripper_rate=100.0))
    t_act3, t_rob3, t_obs3 = make_default_processors()
    features3 = combine_feature_dicts(
        aggregate_pipeline_dataset_features(
            pipeline=t_act3, initial_features=create_initial_features(action=robot3.action_features), use_videos=True),
        aggregate_pipeline_dataset_features(
            pipeline=t_obs3, initial_features=create_initial_features(observation=robot3.observation_features), use_videos=True),
    )
    teleop3.connect()
    if teleop3.listener is not None:
        teleop3.listener.stop()
        teleop3.listener = None
    dataset3 = LeRobotDataset.create(
        "local/so101_mujoco_smoke_vision", FPS, root=root3, robot_type=robot3.name,
        features=features3, use_videos=True)

    def inject3() -> None:
        time.sleep(0.3)
        teleop3._on_press("s")
        time.sleep(0.8)
        teleop3._on_release("s")

    th3 = threading.Thread(target=inject3, daemon=True)
    th3.start()
    try:
        with VideoEncodingManager(dataset3):
            record_loop(
                robot=robot3, events={"exit_early": False}, fps=FPS,
                teleop_action_processor=t_act3, robot_action_processor=t_rob3,
                robot_observation_processor=t_obs3, teleop=teleop3, dataset=dataset3,
                control_time_s=3.0, single_task="sim vision smoke",
            )
            dataset3.save_episode()
    finally:
        dataset3.finalize()
        robot3.disconnect()
        teleop3.disconnect()
    th3.join(timeout=1.0)

    reloaded3 = LeRobotDataset("local/so101_mujoco_smoke_vision", root=root3)
    check("vision dataset has frames", len(reloaded3) >= 80, f"frames={len(reloaded3)}")
    image_keys = [k for k in reloaded3.features if "images" in k]
    check("image feature in dataset features", bool(image_keys), str(list(reloaded3.features)))
    if image_keys:
        frame0 = reloaded3[0][image_keys[0]]
        shape = tuple(frame0.shape)
        check("video frame decodes", shape in ((3, 480, 640), (480, 640, 3)), f"shape={shape}")

    print("[6] workspace scene + overhead camera")
    import mujoco

    robot4 = SO101MujocoRobot(SO101MujocoRobotConfig(onscreen=False, image_camera="sim_cam", top_camera="top_cam"))
    robot4.connect()
    obs4 = robot4.get_observation()
    check("wrist + top images present immediately after connect", "wrist" in obs4 and "top" in obs4,
          str(sorted(k for k in obs4 if not k.endswith(".pos"))))
    top = obs4.get("top")
    check("top frame uint8 (480, 640, 3)",
          top is not None and top.dtype == np.uint8 and top.shape == (480, 640, 3),
          f"got {None if top is None else (top.dtype, top.shape)}")
    check("top image not blank", top is not None and float(top.std()) > 2.0,
          f"std={0.0 if top is None else float(top.std()):.1f}")
    body_names = {mujoco.mj_id2name(robot4.model, mujoco.mjtObj.mjOBJ_BODY, i) for i in range(robot4.model.nbody)}
    check("cubes + container in scene", {"cube_red", "cube_green", "cube_yellow", "cube_box"} <= body_names)

    # scene auto-reset (what record.py's reset-phase hook calls between episodes)
    bid = mujoco.mj_name2id(robot4.model, mujoco.mjtObj.mjOBJ_BODY, "cube_green")
    jadr = int(robot4.model.jnt_qposadr[int(robot4.model.body_jntadr[bid])])
    spawn = robot4.model.qpos0[jadr:jadr + 3].copy()
    with robot4._lock:
        robot4.data.qpos[jadr:jadr + 3] = [0.40, -0.12, 0.08]
    time.sleep(0.3)
    robot4.reset_scene_objects()
    time.sleep(0.4)
    err = float(np.linalg.norm(robot4.data.qpos[jadr:jadr + 3] - spawn))
    check("reset_scene_objects puts the cube back at spawn", err < 0.005, f"off by {err * 1000:.1f} mm")
    robot4.disconnect()

    print("[7] stray arrow press between episodes cannot empty the next one")
    # Recording-control keys set flags in a shared events dict that record_loop
    # consumes at its first tick. A -> pressed *outside* a running episode (reset
    # phase / the long video encode between episodes) would empty the next episode
    # and crash save_episode with "You must add one or several frames..." (hit
    # twice in real recordings). record.py's hook clears stale flags at episode
    # start; the keyboard listener re-sets them once the episode really runs.
    from record import _install_scene_reset_hook  # noqa: PLC0415

    _install_scene_reset_hook()
    import lerobot.scripts.lerobot_record as lerobot_record_module  # noqa: PLC0415

    robot5 = SO101MujocoRobot(SO101MujocoRobotConfig(onscreen=False))
    teleop5 = SO101KeyboardTeleop(SO101KeyboardTeleopConfig(rate=60.0, gripper_rate=100.0))
    t_act5, t_rob5, t_obs5 = make_default_processors()
    features5 = combine_feature_dicts(
        aggregate_pipeline_dataset_features(
            pipeline=t_act5, initial_features=create_initial_features(action=robot5.action_features), use_videos=False),
        aggregate_pipeline_dataset_features(
            pipeline=t_obs5, initial_features=create_initial_features(observation=robot5.observation_features), use_videos=False),
    )
    root5 = Path(tempfile.gettempdir()) / "so101_mujoco_smoke_flag_ds"
    shutil.rmtree(root5, ignore_errors=True)
    robot5.connect()
    teleop5.connect()
    if teleop5.listener is not None:
        teleop5.listener.stop()  # see [3]: isolate from real key events while testing
        teleop5.listener = None
    dataset5 = LeRobotDataset.create(
        "local/so101_mujoco_smoke_flag", FPS, root=root5, robot_type=robot5.name,
        features=features5, use_videos=False)
    # Simulate the real failure: the flag was set while no episode was running
    # (during the previous episode's save), before this episode's loop starts.
    events5 = {"exit_early": True, "rerecord_episode": False, "stop_recording": False}
    t0 = time.perf_counter()
    try:
        with VideoEncodingManager(dataset5):
            # Patched entry point: the hook must clear the stale flag, then the
            # loop records its full second of frames.
            lerobot_record_module.record_loop(
                robot=robot5, events=events5, fps=FPS,
                teleop_action_processor=t_act5, robot_action_processor=t_rob5,
                robot_observation_processor=t_obs5, teleop=teleop5, dataset=dataset5,
                control_time_s=1.0, single_task="flag smoke",
            )
            dataset5.save_episode()
    finally:
        dataset5.finalize()
        robot5.disconnect()
        teleop5.disconnect()
    elapsed = time.perf_counter() - t0
    frames5 = int(dataset5.meta.total_frames)
    check("stale -> cleared at episode start (episode not emptied)",
          frames5 >= 25 and elapsed > 0.9, f"frames={frames5}, loop ran {elapsed:.2f}s")

    print("\nAll smoke checks passed.")


if __name__ == "__main__":
    main()

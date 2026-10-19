# 06 · Data Recording and Replay

## Recording Command Template

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'

# 录真机（主动臂 → 真机从动臂）
uv run --frozen --with mujoco python examples/so101_mujoco/record.py \
    --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101 \
    --robot.use_degrees=false --robot.max_relative_target=10 \
    --teleop.type=so101_leader_trim --teleop.port=COM163 --teleop.id=juxi_leader \
    --teleop.use_degrees=false \
    --dataset.repo_id=local/juxi_so101_teleop \
    --dataset.root=examples/so101_mujoco/outputs/datasets/real_run1 \
    --dataset.num_episodes=5 --dataset.episode_time_s=600 --dataset.reset_time_s=10 \
    --dataset.single_task="pick up the cube" \
    --dataset.video=false --dataset.push_to_hub=false --play_sounds=false --dataset.no_stamp=true

# 录仿真（主动臂 → 仿真从动臂）
#   把 --robot.* 换成: --robot.type=so101_mujoco
# 录仿真（键盘控制）
#   把 --teleop.* 换成: --teleop.type=so101_keyboard --teleop.rate=150
```

## Key Parameters (easy to get wrong)

| Parameter | Description |
| --- | --- |
| `--dataset.root` | **root is the dataset directory itself** (not a parent directory + repo_id concatenation); use a fresh directory for every recording |
| `--dataset.repo_id` | For local recording this is just an identifier; a real `用户名/名字` is only needed when pushing to the Hub later |
| `--dataset.no_stamp=true` | No timestamp suffix, so the directory/name stays stable; to re-record under the same name, delete the old directory first |
| `--dataset.episode_time_s` | Per-episode **upper limit** (a safety net); in normal operation press `→` to end early |
| `--dataset.reset_time_s` | Unrecorded reset time between episodes; during it the leader arm still drives the follower arm in real time. **When recording in simulation, the cubes automatically teleport back to their initial positions when this phase begins** (see below) |
| `--dataset.video` | Enable only when camera data is needed (must be true for visual datasets; the pyav fallback has been verified to work) |
| `--dataset.rgb_encoder.vcodec` | Video codec. **Dual-camera recording on this machine uses `h264`**: `record.py` injects it by default (the upstream default libsvtav1 fails to allocate memory when the two encode streams open concurrently and crashes the whole session—see [07](07-troubleshooting.md)); if passed explicitly, no injection occurs |
| `--dataset.encoder_threads` | Number of encoder threads. **`record.py` injects 2 by default**: using all cores by default makes the simulation visibly stutter during saving (see [07](07-troubleshooting.md)); limiting each encode stream to 2 threads keeps the simulation smooth while saving; if passed explicitly, no injection occurs |
| `--dataset.push_to_hub` | Direct access to HF from this machine requires a proxy; keep false and push manually after recording |

## Episode Control Keys (global, active throughout recording)

| Key | Action |
| --- | --- |
| `→` or `n` | End the current episode (**save**) |
| `←` or `r` | Discard the current episode and **re-record in place** (use this when a single episode is unsatisfactory; no need to restart the session) |
| `q` | End the whole session and save the dataset (**recommended**) |
| `Esc` | Same as `q` (also disconnects keyboard teleoperation; clean exit has been verified, but prefer `q`) |

**Operating advice**: before recording starts, park the leader arm near the mid-position pose (so the convergence segment where the simulated/real arm "swings over" at the start is not recorded);
once recording starts, hold still for a second before beginning the motion.

## Automatic Scene Reset for Simulation Recording

When recording on real hardware, the "Reset the environment" phase requires you to manually put the cubes back in place. In simulation, the recording launcher (`record.py`)
**automatically teleports the three cubes back to their spawn positions** (zeroing their velocities) when that phase begins, so after ending each episode with `→`,
you only need to move the leader arm back to its starting pose; the cubes return automatically and the next episode starts from the fixed initial scene.
The real follower arm has no such behavior (position objects by hand as usual); `teleoperate.py`/`replay.py` are not affected either.

## Post-Recording Inspection

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

It prints each episode's frame count, duration, action span of the six joints, and tracking error:

- **An episode with action span = 0** is an empty recording (nobody moved); delete it and re-record;
- **A large |action−obs| at the start** is the convergence segment (normal); later in the episode it is generally <10 units.

## Recording "With Video" Data in Simulation (wrist camera)

The simulated robot supports recording the wrist camera in the scene (`sim_cam`) into the dataset as image observations:

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/record.py \
    --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader \
    --teleop.use_degrees=false \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision \
    --dataset.num_episodes=5 --dataset.episode_time_s=600 --dataset.reset_time_s=10 \
    --dataset.single_task="pick up the cube" \
    --dataset.video=true --dataset.push_to_hub=false --play_sounds=false --dataset.no_stamp=true
```

Key points: `--robot.image_camera=sim_cam` (camera name) + `--dataset.video=true` (images go through video encoding; the pyav fallback has been verified to work).
The dataset features will include `observation.images.wrist` (480×640×3). Resolution and frame rate can be adjusted with
`--robot.image_width/--robot.image_height/--robot.image_fps`.
When the window is open (`onscreen=true`, the default), besides the main view window, **a real-time preview window is opened for each camera**
(wrist / top, labeled in the upper-left corner), so you can see at a glance whether both views are working during recording; add
`--robot.preview_cameras=false` if you do not need them. Preview windows refresh at **15 Hz** by default (adjustable via `--robot.preview_fps`)—
they are status displays and do not need to follow the main window's 50 Hz, which makes rendering with 3 windows on screen much lighter.

**Scene and top camera (since 2026-10-16)**: the simulation scene includes a built-in workspace—a mat, three colored cubes (34 mm), and a storage box (see `so101_assets.add_workspace`;
the layout can be rendered and fine-tuned with `preview_workspace.py`); there is also a fixed top camera, `top_cam` (top of the image = direction away from the robot arm).
Adding `--robot.top_camera=top_cam` records the top view as `observation.images.top` (both cameras recorded simultaneously); drop the parameter if you only want the wrist camera.
Video encoding after each episode processes both streams, so a slightly longer wait is normal.

## Replay

```bash
# 仿真空回放（窗口里看轨迹重演）
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision --dataset.episode=0

# 真机回放（同款机制，注意周围环境与录制时一致）
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101 \
    --robot.use_degrees=false --robot.max_relative_target=10 \
    --dataset.repo_id=local/juxi_so101_teleop \
    --dataset.root=examples/so101_mujoco/outputs/datasets/juxi_teleop_run1 --dataset.episode=0
```

> The official `lerobot-replay` entry point does not load this project's plugins; using it directly reports `invalid choice: 'so101_mujoco'`—
> so always use the `replay.py` launcher.

## Dataset Format and Location

The dataset is LeRobotDataset v3: both `action` and `observation.state` are 6-dimensional vectors
(`shoulder_pan.pos … gripper.pos`), consistent with official real-robot datasets, so they can be mixed for training directly.

```
examples/so101_mujoco/outputs/datasets/
└── juxi_teleop_run1/   真机键盘遥操（1 回合 / 2430 帧 / 81s）✅ 保留的真机数据

> 2026-10-16 清理：旧的仿真录制（`sim_run2`、`sim_vision_demo`、`sim_vision_run1/2/3`）
> 已全部删除。**正式数据集 `so101_sim_vision`（双相机 / 5 回合 / 10610 帧 / 353.8s / h264）
> 已于当晚录成 ✅**；每回合单机视频导出在 `outputs/videos/so101_sim_vision/`，
> 双相机预览拼图在 `outputs/renders/sim_vision_epN_dual.png`。
```

## Measured Results from This Session (2026-10-15)

| Session | Content | Result |
| --- | --- | --- |
| Real run1 | Keyboard teleoperation recording on real hardware | 1 episode, 81 s, six-joint span 75~140 units, stable at 30 Hz |
| Real replay | Replay of the same episode | All 2430 frames reproduced, no anomalies |
| Sim run2 | Leader-arm teleoperation recording in simulation | 5 episodes, 157 s, tracking error <12 units for ep1~4 |
| Sim replay ep1 | Replay in the window | Trajectory matches the operation (confirmed) |

## Additional Results (2026-10-16)

| Session | Content | Result |
| --- | --- | --- |
| New leader arm (COM124) | Recalibration (new arm/new servos) | ✅ Calibration succeeded; `so101_leader_trim` zero-point compensation automatically adapted to the new calibration |
| Vision run1 | Leader-arm teleoperation recording in simulation (with video) | 2 episodes / 3177 frames / 106 s @ 29.97 Hz; tracking error ≤2 units throughout (only 0.5 s of convergence on the first frame); `observation.images.wrist` video stored and decode-verified ✅ |
| Vision run2 | Dual-camera continued recording (`--resume`) | ep0 (2776 frames / 92.6 s) intact; when saving ep1 the libsvtav1 encoder OOM-crashed the whole session → switched the encoder to h264 (injected by default by `record.py`) and verified end-to-end (2 episodes × dual-stream encoding); leftovers cleaned up, official re-recording moved to run3 |
| Vision run3 | Official dual-camera recording (h264) | Session 1: ep0 (185.2 s / 5554 frames) + ep1 (72.8 s / 2186 frames) stored intact and passed inspection; repeatedly pressing `→` during the inter-session encoding pause triggered an empty-episode crash (mechanism and protection in [07](07-troubleshooting.md)) → continued the session to record the remaining episodes (5-episode plan) |
| Official recording, first attempt (so101_sim_vision) | Dual camera (h264 + 2 threads + 15 Hz preview windows) | When saving ep0 (82.3 s / 2469 frames) the encoder failed to allocate memory and the whole session crashed (system commit near the limit; see [07](07-troubleshooting.md)) → added **automatic retry on encode failure** and **console muting** (both verified, all 26 smoke tests pass); official re-recording pending a machine restart |
| Official recording (so101_sim_vision) ✅ | Dual-camera leader-arm teleoperation, 5 episodes | **All 5/5 episodes stored**: 61.5 / 53.4 / 101.1 / 62.4 / 75.4 s, 10610 frames total @29.97 Hz, 0 ticks over budget, zero crashes; valid motion on all six axes + gripper throughout; dual-stream video decode verification passed |

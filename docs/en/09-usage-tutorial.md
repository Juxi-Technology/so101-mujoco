# 09 · Complete Usage Tutorial (Arm Setup → Dataset → Watching Videos → Training → Deployment)

> An end-to-end operations manual: follow it once and you can go from "plugging in the leader arm" all the way to "a trained policy doing the work on its own in simulation".
> Prerequisites: the environment is set up as in [01](01-environment.md), and the leader arm is calibrated as in [03](03-hardware-calibration.md)
> (on this machine, `juxi_leader` / COM124). All recording-related pitfalls are collected in [07](07-troubleshooting.md).

## 0 · One-Time Preparation

```bash
# 本机所有 uv 命令都要先设（跨盘缓存特例，见 07）
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
```

Plug in the leader arm and confirm the serial port (**the number can change on every replug**):

```bash
uv run --frozen python -c "from serial.tools import list_ports; print([p.device for p in list_ports.comports()])"
```

Leave room on the desktop: recording opens **3 windows** (main view + `wrist camera - live` + `top camera - live`).

## 1 · Teleoperation Warm-Up (Recommended)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_mujoco \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader \
    --teleop.use_degrees=false
```

Move the leader arm around and confirm the simulated arm follows; before exiting (Ctrl-C), park the leader arm **near the mid-position pose** so there is no large convergence segment when recording starts.

## 2 · Recording (Core Command)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/record.py \
    --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader \
    --teleop.use_degrees=false \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision \
    --dataset.num_episodes=5 --dataset.episode_time_s=600 --dataset.reset_time_s=10 \
    --dataset.single_task="put the cube in the box" \
    --dataset.video=true --dataset.push_to_hub=false --play_sounds=false --dataset.no_stamp=true
```

Key points (for the remaining parameters see the parameter table in [06](06-record-and-replay.md)):

| Item | Description |
| --- | --- |
| `--dataset.root` | **root is the dataset directory itself**; use a fresh directory for each session (startup is refused if a directory with the same name exists) |
| Auto-injected defaults | Video codec `h264`, encoder threads `2`—`record.py` prints two hint lines at startup; pass `--dataset.rgb_encoder.vcodec=...` / `--dataset.encoder_threads=...` explicitly to override (reason in 07) |
| Preview windows | On by default (15 Hz; disable with `--robot.preview_cameras=false`; adjustable via `--robot.preview_fps`) |
| `--dataset.video=true` | Both camera streams stored (`observation.images.wrist / top`); drop `top_camera` if you only want the wrist camera |

## 3 · Operating During Recording

| Key | Action |
| --- | --- |
| `→` or `n` | End the current episode and save |
| `←` or `r` | Discard the current episode and re-record in place |
| `q` | End the whole session and save the dataset |

- After an episode ends the **cubes automatically return to their positions**, so you only need to pull the leader arm back to its starting pose; start the next episode's motion once you see `Recording episode N`.
- During the save phase (tens of seconds) the console prints `[record.py] reset done; saving the episode + encoding videos now`—
  during this time **key presses are safely ignored** (accidental presses cannot damage any episode); wait for the next `Recording episode` line before operating.
- Encode failures have an **automatic retry fallback** (after printing `video encode failed ... retrying once` it retries automatically 3 seconds later); saved episodes are never lost.

## 4 · Inspection

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

How to read the output:

- **Episodes where action span is all 0 (or the gripper is 0)** are empty/invalid recordings; delete and re-record;
- **A large `max |act-obs|` at the start of each episode** is the convergence segment and is normal; later in the episode it should be below ~10 units.

## 5 · Watching Videos

```bash
uv run --frozen python examples/so101_mujoco/export_videos.py \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

Outputs:

- `examples/so101_mujoco/outputs/videos/<数据集名>/epN_top.mp4`, `epN_wrist.mp4` — **one double-clickable video per camera per episode**;
- `examples/so101_mujoco/outputs/renders/<数据集名>_epN_dual.png` — one contact sheet per episode (top view on the top row, wrist on the bottom row, 6 evenly sampled frames), for quick visual inspection (`--no-strips` skips it).

The dataset also contains the original packed videos (multiple episodes concatenated in order into one file):
`outputs/datasets/<数据集名>/videos/observation.images.{top,wrist}/chunk-000/file-000.mp4`.

## 6 · Replay (Optional)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision --dataset.episode=0
```

## 7 · Training

```bash
uv run --frozen lerobot-train \
    --policy.type=act \
    --policy.push_to_hub=false \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision \
    --output_dir=examples/so101_mujoco/outputs/train/act_so101_sim_vision \
    --steps=100000 --batch_size=8 --save_freq=20000 --log_freq=200 \
    --num_workers=4 --wandb.enable=false --policy.device=cpu
```

| Key point | Description |
| --- | --- |
| `--policy.type` | Policy type; **start with `act`** (the best match for this data scale/task); `ls src/lerobot/policies/` shows other options (diffusion / smolvla / pi0, etc.) |
| `--policy.push_to_hub=false` | **Required**—by default it wants to push to HuggingFace Hub and exits with an error if no `repo_id` is configured; to push, change it to `--policy.repo_id=你的用户名/模型名` (requires `hf auth login` first) |
| `--policy.device=cpu` | Use `cpu` on this machine since it has no discrete GPU; on machines with an NVIDIA card, drop this parameter (cuda is used automatically) |
| Artifacts | `output_dir/checkpoints/<步数>/` and `checkpoints/last/pretrained_model/`—point deployment at the latter; the `train_config.json` used for resuming training is also inside |
| Resuming | After an interruption, add to the original command: `--resume=true --config_path=<output_dir>/checkpoints/last/pretrained_model/train_config.json` |

**Expected speed on this machine**: about **2 seconds/step** on pure CPU (batch 2, 480p dual camera; the 12-step smoke test showed loss dropping from 70 to 22, a normal trend).
So this machine is suited to small-step pipeline validation—the tutorial's bundled `outputs/train/smoke_act` is the output of 12 steps;
**for full training (ACT typically on the order of 100k steps), switch to a GPU-equipped machine; the command is identical.**

> Dependency note: training requires the `training` extra (accelerate, etc.). If you see `accelerate is required but not installed`,
> add `--extra training` to the installation command in [01](01-environment.md) and retry.

## 8 · Deployment (Let the Policy Work on Its Own in Simulation)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/rollout.py \
    --policy.path=examples/so101_mujoco/outputs/train/act_so101_sim_vision/checkpoints/last/pretrained_model \
    --strategy.type=base \
    --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --task="put the cube in the box" --duration=30
```

| Key point | Description |
| --- | --- |
| Camera parameters | `--robot.image_camera/--robot.top_camera` **must match those used when recording the dataset** (sim_cam + top_cam), otherwise the policy does not get the views it was trained on |
| `--task` | Must match `--dataset.single_task` used during recording |
| `--duration` | Automatically finish after this many seconds (before finishing it returns the arm to the initial pose and then disconnects); `Ctrl-C` also stops it mid-run |
| To try the pipeline first | Use the tutorial's bundled demo model: `--policy.path=examples/so101_mujoco/outputs/train/smoke_act/checkpoints/last/pretrained_model` (trained for 12 steps; the motions are nearly random—this only validates the pipeline) |
| CPU-only deployment | Policy inference occasionally spikes by 0.5s and prints `Control loop is running slower ... than the target FPS`—it runs in simulation but stutters; no such issue on GPU (the 20s smoke run completed and finished normally) |
| Real-hardware deployment | Replace `--robot.*` with the real robot: `--robot.type=so101_follower --robot.port=COMxx --robot.id=juxi_so101 --robot.use_degrees=false` (remember to leave room on the desktop) |
| Other modes | `--strategy.type=sentry / highlight / dagger / episodic`: record while running / ring-buffer save on keypress / human-in-the-loop correction / episodic recording; see `lerobot-rollout --help` |

## Appendix A · Switching to a conda Environment (Optional)

This repository uses a **uv-managed project-local `.venv`** by default (see [01](01-environment.md)), and run commands need the
`uv run --frozen --with mujoco` prefix. If you prefer conda, **replace the "create environment" step with the three commands below**,
and afterwards **drop the uv prefix from all commands** (run `python examples/...` directly); `UV_CACHE_DIR` is no longer needed either
(that is uv's cross-drive cache quirk and has nothing to do with conda):

```bash
# 一次性：在仓库根目录建好环境（python 版本对齐 01 的 3.12）
conda create -n lerobot-sim python=3.12 -y
conda activate lerobot-sim
pip install -e .            # 安装本仓库 lerobot 及其依赖（含 torch，Windows 上 pip 默认就是 CPU 版）
pip install "mujoco==3.16"  # uv 路线用 --with mujoco 临时提供，conda 路线装成常驻依赖
```

Then, for example, recording becomes:

```bash
python examples/so101_mujoco/record.py --robot.image_camera=sim_cam ...
```

Two caveats:

1. **Version alignment**: `pip install -e .` lets pip resolve versions itself and may not exactly match `uv.lock`;
   for a combination identical to the currently verified environment, use uv to install into the conda environment from the lock file:

   ```bash
   uv pip sync uv.lock --python "$(conda run -n lerobot-sim python -c 'import sys; print(sys.executable)')"
   pip install "mujoco==3.16"
   ```

2. The leader arm's calibration cache is stored in `~/.cache/huggingface/lerobot/calibration/` and is independent of which environment you use; switching environments does not require recalibration.

## Appendix B · Common Pitfalls Quick Reference

| Symptom | In one sentence |
| --- | --- |
| Serial port will not open | List the ports first; the number may have changed (step 0) |
| The console goes quiet for tens of seconds while saving | It is encoding, which is normal; once you see the `saving the episode...` hint, do not press keys |
| Video occasionally stutters during recording | Encoding resource contention during the save window; the control loop itself is unaffected (trust the cadence numbers); see 07 for details |
| Can I recover after one crash? | Saved episodes are never lost; continue with `record.py --resume=true ... --dataset.num_episodes=N` |
| `lerobot-train` reports `'repo_id' argument missing` | It wants to push to the Hub by default: add `--policy.push_to_hub=false` (to push, set `--policy.repo_id` and run `hf auth login` first) |
| The policy does not move or moves erratically during deployment | First check whether `--robot.image_camera/--robot.top_camera` and `--task` match the recording; then check whether it was only trained for very few steps |

All pitfalls and solutions (including memory pressure, encoding OOM, empty episodes, etc.) are in [07 · Troubleshooting](07-troubleshooting.md).

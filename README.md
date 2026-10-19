English | [简体中文](README_zh.md)

# SO-ARM101 × MuJoCo — simulation environment for LeRobot

A ready-to-run MuJoCo simulation of the SO-ARM101 arm: real-CAD robot model (mujoco_menagerie),
a wrist camera mounted on the gripper, an overhead camera, and a small workspace with graspable
cubes and a container box — wired into LeRobot through its official plugin mechanism,
**zero modifications to LeRobot source**.

Supported workflows (switchable with one command each): keyboard or real leader-arm teleoperation
(digital twin), dual-camera dataset recording with automatic scene reset, dataset health checks,
per-episode video export, replay, ACT training, and rolling a trained policy out in the simulator.

**📖 Full tutorial — 11 languages:**
[简体中文](docs/README.md) · [English](docs/en/README.md) · [Deutsch](docs/de/README.md) ·
[Español](docs/es/README.md) · [Français](docs/fr/README.md) · [Italiano](docs/it/README.md) ·
[日本語](docs/ja/README.md) · [한국어](docs/ko/README.md) · [Português (BR)](docs/pt-br/README.md) ·
[Português (PT)](docs/pt-pt/README.md) · [繁體中文](docs/zh-hant/README.md)

## Compatibility & installation

This repository is developed and tested against the
**[Juxi-Technology/lerobot](https://github.com/Juxi-Technology/lerobot) fork** (LeRobot 0.6.2).
Clone that first and check this repository out at `examples/so101_mujoco` — every command in the
docs then works verbatim from the lerobot repository root:

```bash
git clone https://github.com/Juxi-Technology/lerobot.git
cd lerobot
git clone https://github.com/Juxi-Technology/so101-mujoco.git examples/so101_mujoco

# one-time environment setup (CPU wheel; drop UV_TORCH_BACKEND on CUDA machines)
UV_TORCH_BACKEND=cpu uv sync --frozen --extra core_scripts --extra feetech --extra pynput-dep --extra training
```

MuJoCo itself is loaded per command via `uv run --with mujoco` (or `pip install mujoco` when using
a conda environment — see [docs/en/09-usage-tutorial.md](docs/en/09-usage-tutorial.md), appendix A).

**Alternative layout — two sibling folders.** The sim repository does not have to live inside the
LeRobot checkout: it imports LeRobot as a normal package dependency, so it works from any location.
If you prefer two independent checkouts side by side (XLeRobot style), clone them as siblings and
run every command from the lerobot root, pointing the script path at the sibling clone:

```bash
git clone https://github.com/Juxi-Technology/lerobot.git
git clone https://github.com/Juxi-Technology/so101-mujoco.git
cd lerobot
uv run --frozen --with mujoco python ../so101-mujoco/record.py \
    --dataset.root=../so101-mujoco/outputs/datasets/so101_sim_vision
```

The tutorial commands assume the in-repo layout (`examples/so101_mujoco/...`); with the sibling
layout only the script/output paths change — they are plain CLI arguments.

> Windows note: if `uv` reports a cross-drive cache error, point its cache to a local drive once:
> `export UV_CACHE_DIR='C:\Users\<you>\AppData\Local\Temp\uv-cache'`

## Quick start

```bash
# Keyboard drives the simulated arm (MuJoCo window opens)
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py

# Real leader arm drives the simulated arm (digital twin)
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader --teleop.use_degrees=false

# Record a dual-camera dataset (wrist + overhead), 5 episodes
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

During recording: `→`/`n` save the episode · `←`/`r` discard and re-record · `q` finish.
The task cubes reset automatically between episodes, and key presses during the save/encode
pause are safely ignored.

Afterwards:

```bash
# Health check: per-episode frames, joint spans, tracking error
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision --root examples/so101_mujoco/outputs/datasets/so101_sim_vision

# Export per-episode playable mp4s + two-camera preview strips
uv run --frozen python examples/so101_mujoco/export_videos.py \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision

# Train (ACT), then roll the trained policy out back in the simulator
uv run --frozen lerobot-train --policy.type=act --policy.push_to_hub=false \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision \
    --output_dir=examples/so101_mujoco/outputs/train/act_so101 --policy.device=cpu
uv run --frozen --with mujoco python examples/so101_mujoco/rollout.py \
    --policy.path=examples/so101_mujoco/outputs/train/act_so101/checkpoints/last/pretrained_model \
    --strategy.type=base --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --task="put the cube in the box" --duration=30
```

> Training needs the `training` extra (included in the `uv sync` command above).
> `--policy.push_to_hub=false` avoids the Hub push prompt; camera flags and `--task` at rollout
> time must match how the dataset was recorded.

## Repository layout

| Path | Contents |
| --- | --- |
| `docs/` | Tutorial, 10 chapters — Simplified Chinese primary; index at [docs/README.md](docs/README.md) |
| `docs/<lang>/` | The same tutorial in de · en · es · fr · it · ja · ko · pt-br · pt-pt · zh-hant |
| `so101_mujoco_robot.py` | Robot plugin (`--robot.type=so101_mujoco`): the simulated follower arm |
| `so101_keyboard_teleop.py` · `so101_leader_trim.py` | Teleop plugins: keyboard jog / real leader arm with automatic zero-trim |
| `so101_assets.py` | Scene builder: menagerie SO-ARM100 model + cameras + workspace objects |
| `assets/menagerie_so_arm100/` | Vendored mujoco_menagerie SO-ARM100 model (Apache-2.0, see its LICENSE) |
| `assets/camera/` | Wrist-camera bracket (STEP/STL) and pose-tuning tools (`adjust_mount.py`, `adjust_camera.py`) |
| `teleoperate.py` · `record.py` · `replay.py` · `rollout.py` | Launchers: register the plugins, then call the official LeRobot CLI |
| `inspect_dataset.py` · `export_videos.py` | Dataset health check / per-episode video export |
| `smoke_test.py` | 26-check automated regression suite (no hardware needed) |
| `load_and_drive.py` · `hardware_check.py` · `preview_workspace.py` · `step_to_stl.py` | Model drive/render check · read-only servo check · workspace layout renders · STEP→STL helper |
| `reports/` | Model structure summaries from the model-verification session |

## What is not in this repository

Recorded and generated content is excluded via `.gitignore` and produced locally on your machine:
`outputs/` (datasets, exported videos, training checkpoints, renders) and `media/` (calibration videos).

## License

Released under the [Apache License 2.0](LICENSE). Copyright 2026 Juxi Technology.
Third-party attributions (the vendored mujoco_menagerie SO-ARM100 model and its upstream,
The Robot Studio) are listed in [NOTICE](NOTICE). LeRobot itself is a dependency and is not
redistributed in this repository.

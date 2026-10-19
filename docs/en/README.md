# SO-ARM101 × MuJoCo Full Workflow Tutorial (Index)

> 🌐 Languages: [简体中文](../README.md) · **English** · [Deutsch](../de/README.md) · [Español](../es/README.md) · [Français](../fr/README.md) · [Italiano](../it/README.md) · [日本語](../ja/README.md) · [한국어](../ko/README.md) · [Português (BR)](../pt-br/README.md) · [Português (PT)](../pt-pt/README.md) · [繁體中文](../zh-hant/README.md)

> This tutorial documents and reproduces the **complete simulation + real-robot workflow** for the SO-ARM101: from environment setup and model verification to hardware calibration,
> and on to keyboard/leader-arm teleoperation, data recording, and replay. All commands were verified in real-hardware + simulation sessions on 2026-10-15.
>
> Intended audience: users of the Juxi SO-ARM101 kit and internal engineers. No prior knowledge of MuJoCo or LeRobot is required.

## Full Workflow Map (two tracks sharing one set of components)

```
                         ┌──────────────── 共用组件 ────────────────┐
                         │  数据集格式(LeRobotDataset) · 回放 · 未来训练  │
                         └──────────────────────────────────────────┘
                                      ▲                    ▲
        ┌── 真机轨 ──────────────────┘                    └──────────── 仿真轨 ──┐
        │  操控: 主动臂(实体) / 键盘                                      操控: 键盘 / 主动臂(实体) │
        │  被控: 真机从动臂 (COM 串口)                                    被控: MuJoCo 仿真从动臂   │
        │  命令: --robot.type=so101_follower                            命令: --robot.type=so101_mujoco │
        └───────────────────────────────────────────────────────────────────────┘
```

| Chapter | Content | What you get |
| --- | --- | --- |
| [01 Environment Setup](01-environment.md) | uv environment, dependency extras, Windows notes | A runnable environment |
| [02 Simulation Model Verification](02-sim-model-verification.md) | Loading/comparing/drive-rendering three MJCF models | Confidence in the model and simulation behavior |
| [03 Hardware Connection and Calibration](03-hardware-calibration.md) | Serial port identification, read-only initial check, follower/leader arm calibration | Two arms recognized by the software |
| [04 Keyboard Teleoperation](04-keyboard-teleop.md) | Driving real hardware/simulation from the keyboard, rate tuning, safe speed limiting | The quickest way to control the arm manually |
| [05 Leader-Arm Digital Twin](05-leader-digital-twin.md) | Physical leader arm driving the simulated follower arm, zero-point trimming | Digital-twin demos and data collection |
| [06 Data Recording and Replay](06-record-and-replay.md) | Recording on hardware/simulation, episode control, replay, inspection script | A trainable dataset |
| [07 Troubleshooting and Lessons Learned](07-troubleshooting.md) | Every pitfall hit in this workflow, with solutions | A troubleshooting handbook |
| [08 Roadmap](08-roadmap.md) | Cameras, object scenes, automatic data generation, training | The next steps |
| [09 Complete Usage Tutorial](09-usage-tutorial.md) | End-to-end: arm setup → recording → inspection → watching videos → training → simulation deployment; includes a conda environment alternative | From zero to a qualified dataset, then to a policy in action |

## Three Conventions to Remember

1. **Unit convention (aligned across all three)**: the five body joints use **−100~100** (stroke ratio, 0 = mid-stroke), and the gripper uses **0~100**
   (0 = closed). Real hardware (`use_degrees=false`), simulation, and the leader arm all follow this convention; recorded datasets match
   the structure of official real-robot datasets such as `lerobot/svla_so101_pickplace` (6-dimensional vector + joint names).
2. **Role mapping**: the controlled target (real hardware or simulation) always uses `--robot.*`; the controlling device (keyboard/leader arm) always uses `--teleop.*`.
3. **Command prefix on this machine**: all `uv` commands on this development machine require the cache directory to be set first (see [07](07-troubleshooting.md) for the reason):

   ```bash
   export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
   ```

## Verified Environment

| Item | Version |
| --- | --- |
| OS | Windows 11 |
| Python / uv | 3.12.9 / 0.12.5 |
| lerobot | 0.6.2 (this repository, isolated in the project `.venv`, does not affect conda) |
| MuJoCo | 3.16.0 |
| PyTorch | 2.11.0 (CPU build) |
| Hardware | SO-ARM101 leader arm (COM163) + follower arm (COM172), CH343 serial chip |

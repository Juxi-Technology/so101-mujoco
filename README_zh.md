[English](README.md) | 简体中文

# SO-ARM101 × MuJoCo — LeRobot 仿真环境

可直接运行的 SO-ARM101 MuJoCo 仿真环境：真机 CAD 机器人模型（mujoco_menagerie）、装在夹爪上的
腕部相机、固定顶视相机，以及一块带可抓取方块和收纳盒的工作区——通过 LeRobot 官方插件机制接入，
**零修改 LeRobot 源码**。

支持的工作流（每种一行命令即可）：键盘 / 实体主动臂遥操（数字孪生）、双相机数据录制（回合间自动
重置场景）、数据集体检、每回合视频导出、回放、ACT 训练，以及在仿真器里部署训练好的策略。

**📖 完整教程 — 11 种语言：**
[简体中文](docs/README.md) · [English](docs/en/README.md) · [Deutsch](docs/de/README.md) ·
[Español](docs/es/README.md) · [Français](docs/fr/README.md) · [Italiano](docs/it/README.md) ·
[日本語](docs/ja/README.md) · [한국어](docs/ko/README.md) · [Português (BR)](docs/pt-br/README.md) ·
[Português (PT)](docs/pt-pt/README.md) · [繁體中文](docs/zh-hant/README.md)

## 兼容性与安装

本仓库基于并实测于 **[Juxi-Technology/lerobot](https://github.com/Juxi-Technology/lerobot)** fork
（LeRobot 0.6.2）。先克隆该仓库，再把本仓库检出到它的 `examples/so101_mujoco` 目录——这样文档里的
每条命令都可以在 lerobot 仓库根目录原样执行：

```bash
git clone https://github.com/Juxi-Technology/lerobot.git
cd lerobot
git clone https://github.com/Juxi-Technology/so101-mujoco.git examples/so101_mujoco

# 一次性环境安装（CPU 版 torch；CUDA 机器去掉 UV_TORCH_BACKEND）
UV_TORCH_BACKEND=cpu uv sync --frozen --extra core_scripts --extra feetech --extra pynput-dep --extra training
```

MuJoCo 本体按命令临时加载：`uv run --with mujoco`（使用 conda 环境时装成常驻依赖
`pip install mujoco` 即可——见 [docs/09 附录 A](docs/09-usage-tutorial.md)）。

**另一种布局——两个并列的独立文件夹。** 本仓库不必须放在 lerobot 检出目录里面：它以普通包依赖
的方式引用 LeRobot，放在任何位置都能工作。如果你更喜欢两个相互独立的检出并排摆放（XLeRobot 风格），
把两者克隆为兄弟目录，然后**在 lerobot 根目录执行**所有命令、脚本路径指向兄弟仓库即可：

```bash
git clone https://github.com/Juxi-Technology/lerobot.git
git clone https://github.com/Juxi-Technology/so101-mujoco.git
cd lerobot
uv run --frozen --with mujoco python ../so101-mujoco/record.py \
    --dataset.root=../so101-mujoco/outputs/datasets/so101_sim_vision
```

教程里的命令约定用仓库内布局（`examples/so101_mujoco/...`）；换成兄弟布局时只需改脚本/输出路径——
它们本来都是命令行参数。

> Windows 提示：如果 `uv` 报跨盘缓存错误，把缓存指到本地盘一次即可：
> `export UV_CACHE_DIR='C:\Users\<you>\AppData\Local\Temp\uv-cache'`

## 快速开始

```bash
# 键盘驱动仿真臂（自动打开 MuJoCo 窗口）
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py

# 实体主动臂驱动仿真臂（数字孪生）
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader --teleop.use_degrees=false

# 录一份双相机数据集（腕部 + 顶视），5 个回合
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

录制中：`→`/`n` 保存回合 · `←`/`r` 丢弃重录 · `q` 收尾。回合间方块自动归位；
保存/编码停顿期的按键会被安全忽略。

录制之后：

```bash
# 体检：每回合帧数、关节动作幅度、跟随误差
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision --root examples/so101_mujoco/outputs/datasets/so101_sim_vision

# 导出每回合可播放 mp4 + 双相机预览拼图
uv run --frozen python examples/so101_mujoco/export_videos.py \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision

# 训练（ACT），然后在仿真器里部署训练好的策略
uv run --frozen lerobot-train --policy.type=act --policy.push_to_hub=false \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision \
    --output_dir=examples/so101_mujoco/outputs/train/act_so101 --policy.device=cpu
uv run --frozen --with mujoco python examples/so101_mujoco/rollout.py \
    --policy.path=examples/so101_mujoco/outputs/train/act_so101/checkpoints/last/pretrained_model \
    --strategy.type=base --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --task="put the cube in the box" --duration=30
```

> 训练需要 `training` extra（上面的 `uv sync` 命令已包含）。`--policy.push_to_hub=false` 避免
> Hub 推送报错；部署时的相机参数与 `--task` 必须与录制数据集时一致。

## 仓库结构

| 路径 | 内容 |
| --- | --- |
| `docs/` | 教程（10 章，简体中文主版本），索引在 [docs/README.md](docs/README.md) |
| `docs/<lang>/` | 同一套教程的 de · en · es · fr · it · ja · ko · pt-br · pt-pt · zh-hant 版本 |
| `so101_mujoco_robot.py` | Robot 插件（`--robot.type=so101_mujoco`）：仿真从动臂 |
| `so101_keyboard_teleop.py` · `so101_leader_trim.py` | Teleop 插件：键盘点动 / 实体主动臂+自动零点微调 |
| `so101_assets.py` | 场景构建：menagerie SO-ARM100 模型 + 相机 + 工作区物体 |
| `assets/menagerie_so_arm100/` | vendored mujoco_menagerie SO-ARM100 模型（Apache-2.0，见其 LICENSE） |
| `assets/camera/` | 腕部相机支架（STEP/STL）与位姿调参工具（`adjust_mount.py`、`adjust_camera.py`） |
| `teleoperate.py` · `record.py` · `replay.py` · `rollout.py` | 启动器：注册插件后调用官方 LeRobot 入口 |
| `inspect_dataset.py` · `export_videos.py` | 数据集体检 / 每回合视频导出 |
| `smoke_test.py` | 26 项自动回归测试（无需硬件） |
| `load_and_drive.py` · `hardware_check.py` · `preview_workspace.py` · `step_to_stl.py` | 模型驱动/渲染验证 · 只读硬件体检 · 工作区布局渲染 · STEP→STL 工具 |
| `reports/` | 模型验证阶段的结构摘要 |

## 仓库不包含的内容

录制与生成的产物通过 `.gitignore` 排除，均在你的机器本地生成：
`outputs/`（数据集、导出视频、训练 checkpoint、渲染图）与 `media/`（标定对照视频）。

## 许可证

以 [Apache License 2.0](LICENSE) 发布，版权归 Juxi Technology（2026）。
第三方声明（vendored 的 mujoco_menagerie SO-ARM100 模型及其上游 The Robot Studio）见 [NOTICE](NOTICE)；
LeRobot 本体是依赖项，本仓库不包含其源码。

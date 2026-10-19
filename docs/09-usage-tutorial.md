# 09 · 完整使用教程（开臂 → 数据集 → 看视频 → 训练 → 部署）

> 一条龙操作手册：照着走一遍，就能从"插上主动臂"一路走到"训练好的策略自己在仿真里干活"。
> 前提：环境已按 [01](01-environment.md) 装好、主动臂已按 [03](03-hardware-calibration.md) 标定
> （本机为 `juxi_leader` / COM124）。所有录制相关的坑集中在 [07](07-troubleshooting.md)。

## 0 · 一次性准备

```bash
# 本机所有 uv 命令都要先设（跨盘缓存特例，见 07）
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
```

插上主动臂，确认串口（**每次插拔都可能变号**）：

```bash
uv run --frozen python -c "from serial.tools import list_ports; print([p.device for p in list_ports.comports()])"
```

桌面留出空间：录制会弹出 **3 个窗口**（主视角 + `wrist camera - live` + `top camera - live`）。

## 1 · 遥操热身（推荐）

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_mujoco \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader \
    --teleop.use_degrees=false
```

动一动主动臂，确认仿真臂跟手；退出（Ctrl-C）前把主动臂停到**中位姿态附近**，开录瞬间不会有大收敛段。

## 2 · 录制（核心命令）

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

要点（其余参数见 [06](06-record-and-replay.md) 参数表）：

| 项 | 说明 |
| --- | --- |
| `--dataset.root` | **root 就是数据集目录本身**，每场换一个新目录（同名目录存在会拒启） |
| 自动注入的默认值 | 视频编码 `h264`、编码线程 `2`——`record.py` 启动时打印两行提示；显式传 `--dataset.rgb_encoder.vcodec=...` / `--dataset.encoder_threads=...` 可覆盖（原因见 07） |
| 预览窗 | 默认开（15Hz，`--robot.preview_cameras=false` 可关；`--robot.preview_fps` 可调） |
| `--dataset.video=true` | 双相机画面入库（`observation.images.wrist / top`）；只要腕部相机就去掉 `top_camera` |

## 3 · 录制中的操作

| 按键 | 作用 |
| --- | --- |
| `→` 或 `n` | 结束当前回合并保存 |
| `←` 或 `r` | 丢弃当前回合，原地重录 |
| `q` | 整场结束，保存数据集 |

- 回合结束后**方块自动归位**，你只需要把主动臂拉回起始姿态；看到 `Recording episode N` 再开始下一回合的动作。
- 保存阶段（几十秒）控制台会打印 `[record.py] reset done; saving the episode + encoding videos now`——
  这段时间**按键会被安全忽略**（误按不会弄坏任何回合），等下一行 `Recording episode` 出现再操作。
- 编码失败有**自动重试兜底**（打印 `video encode failed ... retrying once` 后 3 秒自动重试）；已保存的回合永不丢失。

## 4 · 体检

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

怎么读输出：

- **action span 全为 0（或夹爪为 0）的回合**是空录/无效录制，删除重录；
- **每回合开头 `max |act-obs|` 偏大**是收敛段，正常；中后段应小于 ~10 单位。

## 5 · 看视频

```bash
uv run --frozen python examples/so101_mujoco/export_videos.py \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

产物：

- `examples/so101_mujoco/outputs/videos/<数据集名>/epN_top.mp4`、`epN_wrist.mp4` —— **每回合每相机一个可双击播放的视频**；
- `examples/so101_mujoco/outputs/renders/<数据集名>_epN_dual.png` —— 每回合一张拼图（上排顶视、下排腕部，均匀采样 6 帧），快速目检用（`--no-strips` 可跳过）。

数据集里也有原始打包视频（多回合按顺序拼在同一个文件）：
`outputs/datasets/<数据集名>/videos/observation.images.{top,wrist}/chunk-000/file-000.mp4`。

## 6 · 回放（可选）

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision --dataset.episode=0
```

## 7 · 训练

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

| 要点 | 说明 |
| --- | --- |
| `--policy.type` | 策略类型，**`act` 起步**（与这套数据规模/任务最匹配）；`ls src/lerobot/policies/` 可看其他选择（diffusion / smolvla / pi0 等） |
| `--policy.push_to_hub=false` | **必加**——默认想推 HuggingFace Hub，没配 `repo_id` 会直接报错退出；要推时改为 `--policy.repo_id=你的用户名/模型名`（需先 `hf auth login`） |
| `--policy.device=cpu` | 本机无独显用 `cpu`；有 NVIDIA 卡的机器删掉该参数（自动用 cuda） |
| 产物 | `output_dir/checkpoints/<步数>/` 与 `checkpoints/last/pretrained_model/`——部署指向后者；续训用的 `train_config.json` 也在里面 |
| 续训 | 中断后原命令加：`--resume=true --config_path=<output_dir>/checkpoints/last/pretrained_model/train_config.json` |

**本机速度预期**：纯 CPU 约 **2 秒/步**（batch 2、480p 双相机；实测 12 步冒烟 loss 从 70 降到 22，方向正常）。
所以本机适合小步数验证链路——教程自带的 `outputs/train/smoke_act` 就是 12 步的产物；
**正式训练（ACT 常规 10 万步量级）建议换带 GPU 的机器，命令完全一样。**

> 依赖提示：训练需要 `training` extra（accelerate 等）。若报 `accelerate is required but not installed`，
> 按 [01](01-environment.md) 的安装命令补上 `--extra training` 后重试。

## 8 · 部署（让策略在仿真里自己干活）

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/rollout.py \
    --policy.path=examples/so101_mujoco/outputs/train/act_so101_sim_vision/checkpoints/last/pretrained_model \
    --strategy.type=base \
    --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --task="put the cube in the box" --duration=30
```

| 要点 | 说明 |
| --- | --- |
| 相机参数 | `--robot.image_camera/--robot.top_camera` **必须与录制数据集时一致**（sim_cam + top_cam），否则策略拿不到它训练过的画面 |
| `--task` | 与录制时的 `--dataset.single_task` 一致 |
| `--duration` | 跑满多少秒自动收场（收场前会把机械臂送回初始位姿再断开）；中途 `Ctrl-C` 也可停 |
| 想先试通链路 | 用教程自带演示模型即可：`--policy.path=examples/so101_mujoco/outputs/train/smoke_act/checkpoints/last/pretrained_model`（12 步训练，动作接近乱动，只验证链路） |
| 纯 CPU 部署 | 策略推理偶发 0.5s 尖峰，会提示 `Control loop is running slower ... than the target FPS`——仿真里能跑但会顿；GPU 上无此问题（实测 20s 冒烟全程可跑、正常收场） |
| 真机部署 | 把 `--robot.*` 换成真机：`--robot.type=so101_follower --robot.port=COMxx --robot.id=juxi_so101 --robot.use_degrees=false`（注意桌面留出空间） |
| 其他模式 | `--strategy.type=sentry / highlight / dagger / episodic`：边跑边录 / 环形缓冲按键存 / 人在回路纠偏 / 回合制录制，见 `lerobot-rollout --help` |

## 附录 A · 换成 conda 环境（可选）

本仓库默认用 **uv 管理的项目内 `.venv`**（见 [01](01-environment.md)），运行命令都要带
`uv run --frozen --with mujoco` 前缀。如果你更习惯 conda，做法是**把"建环境"那一步换成下面三条**，
之后**所有命令去掉 uv 前缀**（`python examples/...` 直接跑），`UV_CACHE_DIR` 也不再需要
（那是 uv 的跨盘缓存特例，与 conda 无关）：

```bash
# 一次性：在仓库根目录建好环境（python 版本对齐 01 的 3.12）
conda create -n lerobot-sim python=3.12 -y
conda activate lerobot-sim
pip install -e .            # 安装本仓库 lerobot 及其依赖（含 torch，Windows 上 pip 默认就是 CPU 版）
pip install "mujoco==3.16"  # uv 路线用 --with mujoco 临时提供，conda 路线装成常驻依赖
```

之后例如录制就变成：

```bash
python examples/so101_mujoco/record.py --robot.image_camera=sim_cam ...
```

两个注意点：

1. **版本对齐**：`pip install -e .` 由 pip 自行解析版本，未必和 `uv.lock` 完全一致；
   想要与当前实测环境一字不差的组合，用 uv 往 conda 环境里按锁文件装：

   ```bash
   uv pip sync uv.lock --python "$(conda run -n lerobot-sim python -c 'import sys; print(sys.executable)')"
   pip install "mujoco==3.16"
   ```

2. 主动臂的标定缓存存在 `~/.cache/huggingface/lerobot/calibration/`，与用哪个环境无关，迁移环境不用重标。

## 附录 B · 常见坑速查

| 现象 | 一句话 |
| --- | --- |
| 串口打不开 | 先列端口，号可能变了（第 0 步） |
| 保存时控制台安静几十秒 | 正在编码，属正常；看到 `saving the episode...` 提示就别按键 |
| 录制时画面偶发卡顿 | 保存窗口的编码资源竞争；控制回路本身不受影响（cadence 数字为准），详见 07 |
| 崩了一次还能救吗 | 已保存回合永不丢；`record.py --resume=true ... --dataset.num_episodes=N` 续录 |
| `lerobot-train` 报 `'repo_id' argument missing` | 默认想推 Hub：加 `--policy.push_to_hub=false`（要推就配 `--policy.repo_id` 并先 `hf auth login`） |
| 部署时策略不动或乱动 | 先核对 `--robot.image_camera/--robot.top_camera` 和 `--task` 是否与录制时一致；再看是否只训了很少步数 |

全部坑与解法（含内存吃紧、编码 OOM、空回合等）见 [07 · 常见问题](07-troubleshooting.md)。

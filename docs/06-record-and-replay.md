# 06 · 数据录制与回放

## 录制命令模板

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

## 参数要点（容易踩的）

| 参数 | 说明 |
| --- | --- |
| `--dataset.root` | **root 就是数据集目录本身**（不是父目录 + repo_id 拼接）；每次录制换一个新目录 |
| `--dataset.repo_id` | 本地录制只是标识符；将来推 Hub 时才需要真实的 `用户名/名字` |
| `--dataset.no_stamp=true` | 不加时间戳后缀，目录/名字稳定；重录同名需先删除旧目录 |
| `--dataset.episode_time_s` | 单回合**上限**（保险）；正常操作按 `→` 提前结束 |
| `--dataset.reset_time_s` | 回合间不记录的归位时间；期间主动臂仍实时驱动从动臂。**仿真录制时方块会在进入该阶段时自动瞬移回初始位置**（见下） |
| `--dataset.video` | 需要相机数据时才开（视觉数据集必须 true；pyav 回退已验证可用） |
| `--dataset.rgb_encoder.vcodec` | 视频编码器。**本机双相机录制用 `h264`**：`record.py` 已默认注入（上游默认 libsvtav1 两路编码并发打开时会内存分配失败、整场崩溃——见 [07](07-troubleshooting.md)）；显式传入则不再注入 |
| `--dataset.encoder_threads` | 编码线程数。**`record.py` 默认注入 2**：默认吃满全核会让保存期的仿真画面明显卡顿（见 [07](07-troubleshooting.md)）；每路编码限 2 线程后保存时仿真保持顺滑；显式传入则不再注入 |
| `--dataset.push_to_hub` | 本机直连 HF 需代理，先保持 false，录制完手动推 |

## 回合控制键（全局，录制期间一直有效）

| 按键 | 作用 |
| --- | --- |
| `→` 或 `n` | 结束当前回合（**保存**） |
| `←` 或 `r` | 丢弃当前回合并**原地重录**（单回合不满意用它，不必重启会话） |
| `q` | 整场结束，保存数据集（**推荐**） |
| `Esc` | 同 `q`（会顺带断开键盘遥操；已验证干净退出，但仍优先用 `q`） |

**操作建议**：开录前把主动臂停在中位姿态附近（避免开录一瞬仿真臂/真机臂"甩过去"的收敛段被录进去）；
开录后先做一秒静止再开始动作。

## 仿真录制的自动场景重置

真机录制时，"Reset the environment"阶段需要你手动把方块放回原位。仿真里录制启动器（`record.py`）
会在该阶段开始时**自动把三个方块瞬移回出生位**（同时清零速度），所以每回合按 `→` 结束后，
你只需要把主动臂移回起始姿态，方块会自动归位，下一回合从固定的初始场景开始。
真机从动臂没有这个行为（照常手动摆放）；`teleoperate.py`/`replay.py` 也不涉及。

## 录制后体检

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

输出每回合的帧数、时长、六关节动作幅度与跟随误差：

- **action span = 0 的回合**是空录（人没动），删除重录即可；
- **开头的 |action−obs| 很大**是收敛段（正常），中后段一般 <10 单位。

## 仿真里录"带画面"的数据（wrist 相机）

仿真机器人支持把场景里的腕部相机（`sim_cam`）作为图像观测录进数据集：

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

要点：`--robot.image_camera=sim_cam`（相机名）+ `--dataset.video=true`（图像走视频编码，pyav 回退已验证可用）。
数据集特征里会出现 `observation.images.wrist`（480×640×3）。分辨率和帧率可用
`--robot.image_width/--robot.image_height/--robot.image_fps` 调整。
开窗口时（`onscreen=true`，默认）除了主视角窗口，还会为**每个相机各开一个实时预览窗口**
（腕部 / 俯视，窗口左上角有标注），录制时可直接看到两路画面是否正常；不需要就加
`--robot.preview_cameras=false`。预览窗默认按 **15Hz** 刷新（`--robot.preview_fps` 可调）——
它们是状态显示、不必跟随主窗口的 50Hz，这样同屏 3 个窗口时渲染负担小得多。

**场景与顶视相机（2026-10-16 起）**：仿真场景自带工作区——垫板、三色方块（34mm）、收纳盒（见 `so101_assets.add_workspace`，
布局可用 `preview_workspace.py` 渲染微调）；另有一台固定顶视相机 `top_cam`（画面上方 = 远离机械臂方向）。
加 `--robot.top_camera=top_cam` 即把顶视画面录成 `observation.images.top`（双相机同时录）；只要腕部相机就去掉该参数。
单回合结束后的视频编码会同时处理两路画面，等待时间略长属正常。

## 回放

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

> 官方 `lerobot-replay` 入口不加载本项目插件，直接用会报 `invalid choice: 'so101_mujoco'`——
> 所以统一走 `replay.py` 启动器。

## 数据集格式与位置

数据集为 LeRobotDataset v3：`action` 与 `observation.state` 均为 6 维向量
（`shoulder_pan.pos … gripper.pos`），与官方真机数据集一致，可直接混合训练。

```
examples/so101_mujoco/outputs/datasets/
└── juxi_teleop_run1/   真机键盘遥操（1 回合 / 2430 帧 / 81s）✅ 保留的真机数据

> 2026-10-16 清理：旧的仿真录制（`sim_run2`、`sim_vision_demo`、`sim_vision_run1/2/3`）
> 已全部删除。**正式数据集 `so101_sim_vision`（双相机 / 5 回合 / 10610 帧 / 353.8s / h264）
> 已于当晚录成 ✅**；每回合单机视频导出在 `outputs/videos/so101_sim_vision/`，
> 双相机预览拼图在 `outputs/renders/sim_vision_epN_dual.png`。
```

## 本次实测记录（2026-10-15）

| 会话 | 内容 | 结果 |
| --- | --- | --- |
| 真机 run1 | 键盘遥操录真机 | 1 回合 81s，六关节幅度 75~140 单位，30Hz 稳定 |
| 真机回放 | 同回合重放 | 2430 帧完整重现，无异常 |
| 仿真 run2 | 主动臂遥操录仿真 | 5 回合 157s，ep1~4 跟随误差 <12 单位 |
| 仿真回放 ep1 | 窗口重演 | 轨迹与操作一致（已确认） |

## 追加实测（2026-10-16）

| 会话 | 内容 | 结果 |
| --- | --- | --- |
| 新主动臂（COM124） | 重新标定（新臂/新舵机）| ✅ 标定成功；`so101_leader_trim` 零点补偿自动按新标定适配 |
| 视觉 run1 | 主动臂遥操录仿真（带画面）| 2 回合 / 3177 帧 / 106s @ 29.97Hz；跟随误差全程 ≤2 单位（仅首帧收敛 0.5s）；`observation.images.wrist` 视频入库并解码验证 ✅ |
| 视觉 run2 | 双相机续录（`--resume`）| ep0（2776 帧 / 92.6s）无损；ep1 保存时 libsvtav1 编码器 OOM 整场崩溃 → 编码器改 h264（`record.py` 默认注入）并端到端实测通过（2 回合 × 双路编码）；残留已清理，正式重录转入 run3 |
| 视觉 run3 | 双相机正式录制（h264）| 第 1 场：ep0（185.2s / 5554 帧）+ ep1（72.8s / 2186 帧）入库完好、体检通过；场间编码停顿期连按 `→` 触发空回合崩溃（机制与防护见 [07](07-troubleshooting.md)）→ 续场录余下回合（5 回合计划）|
| 正式录制首战（so101_sim_vision）| 双相机（h264 + 2 线程 + 预览窗 15Hz）| ep0（82.3s / 2469 帧）保存时编码器内存分配失败整场崩溃（系统 commit 近满，见 [07](07-troubleshooting.md)）→ 已加**编码失败自动重试**与**控制台静音**（均实测生效，冒烟 26 项全过）；待重启机器后正式重录 |
| 正式录制（so101_sim_vision）✅ | 双相机主动臂遥操，5 回合 | **5/5 回合全部入库**：61.5 / 53.4 / 101.1 / 62.4 / 75.4 s，共 10610 帧 @29.97Hz、0 tick 超预算、零崩溃；六轴+夹爪全程有效动作；双路视频解码核验通过 |

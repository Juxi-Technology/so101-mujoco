# 04 · 键盘遥操

用键盘"点动"关节来手动控制真机或仿真臂——不需要主动臂时的最快控制方式，也是录制演示数据的手段之一。

## 命令

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'

# 真机从动臂
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101 \
    --robot.use_degrees=false --robot.max_relative_target=5 \
    --teleop.type=so101_keyboard --teleop.rate=150

# 仿真从动臂（MuJoCo 窗口自动打开）
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --teleop.rate=150
```

（`teleoperate.py` 默认就是 `--robot.type=so101_mujoco --teleop.type=so101_keyboard`。）

## 按键（按住生效，全局监听——窗口聚焦在哪里都行）

| 按键 | 动作 | 按键 | 动作 |
| --- | --- | --- | --- |
| `w` / `s` | shoulder_lift 上 / 下 | `a` / `z` | shoulder_pan 左 / 右 |
| `e` / `d` | elbow_flex 伸 / 屈 | `t` / `g` | wrist_flex + / − |
| `y` / `h` | wrist_roll + / − | `u` / `j` | 夹爪 张开 / 闭合 |

按键是**刻意避开录制控制键**（`n/r/q`、方向键、`Esc`）选的，这样遥操和录制可以同时跑。

## 关键参数

| 参数 | 作用 | 建议值 |
| --- | --- | --- |
| `--teleop.rate` | 按住键时目标速度（单位/秒） | 默认 60 偏慢；实机手感 **150** 比较合适 |
| `--robot.max_relative_target` | 每个控制周期最多让关节移动多少单位（安全限速） | 真机 **5**（60Hz 遥操）/ **10**（30Hz 录制） |
| `--robot.use_degrees=false` | 用行程比例制（−100~100）而非角度制 | **真机必加**，否则单位对不上（仿真默认一致） |

## 行为说明

- **遥操期间不要打字**：键盘监听是**全局且不吞键**的——在电脑上任何窗口敲到映射键
  （`w a s z e d t g y h u j`，包括聊天框里的拼音）都会同时驱动手臂。用主动臂模式没有这个问题。
- **连接瞬间手臂会移动**：真机从动臂先上扭矩（变硬），然后朝"中点姿态"移动（按下键前的目标）；
  仿真臂直接朝中点位姿收敛。保持手边留空间。
- **退出**：对该终端 `Ctrl-C`（或按 `Esc`，键盘监听会断开并干净退出）。退出后真机会**失扭矩变软**，
  手扶一下——这是正常行为。
- **启动日志里成串的 `clamped to be safe` WARNING** 是限速器在"追赶"时的正常输出，到位后自动停止。

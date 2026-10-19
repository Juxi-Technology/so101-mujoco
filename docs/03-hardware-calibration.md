# 03 · 实机连接与标定

## 识别串口

CH343 芯片的驱动板插上后即出现一个 COM 口；**编号会随插拔/换 USB 口变化**，每次连接前先确认：

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen python -c "import serial.tools.list_ports as lp; [print(p.device, '|', p.description, '|', p.hwid) for p in lp.comports()]"
```

## 第一步：只读初检（接线/供电/舵机体检）

**不写任何东西**，先把六颗舵机挨个 ping 一遍再读电压温度（扭矩状态原样保留）：

```bash
uv run --frozen python examples/so101_mujoco/hardware_check.py --port COM163
```

正常输出形如：六行关节、温度 20~30°C、扭矩 0（手臂自由）。**电压视供电方式而定**：从动臂接外接
电源时约 11V，主动臂仅靠驱动板供电时约 5V——能把六颗舵机全部读完即为接线正常。有缺失/型号不符
会直接报错。

## 第二步：标定

标定把"每个关节的行程范围 + 中位参考"写进舵机 EEPROM 并保存到本地文件；**从动臂和主动臂都要各标一次**。
两台臂的标定文件分开存放，互不影响：

| 设备 | 命令 | 标定文件落点 |
| --- | --- | --- |
| 从动臂 | `uv run --frozen lerobot-calibrate --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101` | `~/.cache/huggingface/lerobot/calibration/robots/so_follower/juxi_so101.json` |
| 主动臂 | `uv run --frozen lerobot-calibrate --teleop.type=so101_leader --teleop.port=COM163 --teleop.id=juxi_leader` | `.../calibration/teleoperators/so_leader/juxi_leader.json` |

`id` 可以任意起名，但**之后遥操/录制必须使用同一个 id**，否则会再次提示标定。

### 物理步骤（终端会打印示意图）

1. **摆到中位姿态再回车**：底座平放桌面边缘，大臂竖直向上、小臂水平朝前，肩部旋转与腕部居中
   （主动臂的"夹爪"是手柄/扳机）。这一刻的位置被记为该臂的"中位参考"。
2. 回车后**逐个关节缓慢划过整个活动范围**（`wrist_roll` 不用扫，自动按全圈处理），再回车保存。

注意事项：

- 从动臂标定期间扭矩为 0（手臂是软的），用手扶着动；主动臂本来就无扭矩。
- 标定过程会向舵机写 EEPROM（这是标定的一部分，正常）。
- 本次实测标定结果（供对照）：从动臂各关节行程 1474~2688 计数、`wrist_roll` 4095；
  主动臂 2208~2681 计数。行程明显不对称是正常的（见 [05 零点微调](05-leader-digital-twin.md) 为何要做）。

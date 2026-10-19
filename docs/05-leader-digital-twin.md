# 05 · 主动臂数字孪生（实体臂驱动仿真臂）

用手拖动**实体主动臂**，让 **MuJoCo 窗口里的仿真从动臂**实时镜像跟随——数字孪生演示、
仿真数据采集的正确开法。

## 前置

主动臂已标定（见 [03](03-hardware-calibration.md)），串口以 `COM163` 为例。

## 命令

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_mujoco \
    --teleop.type=so101_leader_trim --teleop.port=COM163 --teleop.id=juxi_leader \
    --teleop.use_degrees=false
```

- `--robot.type=so101_mujoco`：被控对象是仿真臂，窗口自动打开；
- `--teleop.*`：操控设备是实体主动臂（纯读取，永不上扭矩，对主动臂零风险）；
- `--teleop.use_degrees=false`：**必加**。让主动臂输出的单位（行程比例制）与仿真臂一致。

把 `--robot.type` 换成 `so101_follower --robot.port=COM172 --robot.id=juxi_so101 --robot.max_relative_target=5`
就是"实体主动臂 → 真机从动臂"的常规套件玩法，同一份主动臂标定通用。

## 零点是偏的怎么办：自动中心微调（`so101_leader_trim`）

**现象**：主动臂摆到"目视中位"，仿真臂却偏几度。

**原理**：lerobot 的归一化零点 = **标定时扫掠记录范围的中点** `(min+max)/2`；而标定回车时的
"中位姿态"被记成原始值 2048。只要某个关节的机械行程本身不对称，两个"中点"就永远差一个固定量
（实测 1 号舵机：记录范围 776~3457，中点 2116，与 2048 差 68 计数 ≈ **5.6°**）。
**这个偏差重新标定消不掉**（行程不对称是机械结构决定的），必须在软件里补偿。

**解法**：`so101_leader_trim` 插件从标定文件里按公式自动算出每个关节的补偿并实时减掉，
重新标定后自动跟随、无需手工调参：

```
补偿ᵢ = (2048 − minᵢ) / (maxᵢ − minᵢ) × 200 − 100
```

本机实测生效值（启动日志会打印）：

| 关节 | 补偿（单位） |
| --- | --- |
| shoulder_pan | −5.11 |
| shoulder_lift | −0.92 |
| elbow_flex | +2.54 |
| wrist_flex | +0.69 |

其余关节偏差 <0.05，无需补偿；夹爪（0~100）与角度制模式不参与微调。

> 开发者注记：该插件的 `name` 必须保持 `"so_leader"`——`name` 是标定文件的查找目录键，
> 自定义类型名会导致找不到标定文件而误触发重新标定流程。

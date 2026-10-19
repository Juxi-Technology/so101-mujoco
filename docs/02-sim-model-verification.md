# 02 · 仿真模型验证（MJCF 加载与驱动）

## 模型来源

SO-ARM101 的三份公开 MJCF 模型，本项目全部验证可用：

| 简称 | 文件 | 来源 |
| --- | --- | --- |
| 官方-新校准 | `SO101/so101_new_calib.xml` | TheRobotStudio/SO-ARM100 官方仓库；**本仓库教程 zip 内有同款副本**（逐字节一致） |
| 官方-旧校准 | `SO101/so101_old_calib.xml` | 同仓库（zip 中没有，需下载） |
| ROS2 描述包 | `so_arm101_description/mjcf/so_arm101.xml` | 本仓库教程附件 `SO-ARM101_ROS2.zip` |

注：zip 提取流程由早期版 `so101_assets.py` 提供并保留可查；2026-10-16 起仿真机器人已迁移到
**mujoco_menagerie 的 SO-ARM100 模型**（vendored 于 `assets/menagerie_so_arm100/`，
迁移原因与要点见 [07](07-troubleshooting.md) 设计说明）。

## 驱动与渲染验证

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen --with mujoco python examples/so101_mujoco/load_and_drive.py \
    --model "<模型路径>" --out-dir out
```

脚本会输出结构摘要（关节/执行器/增益/范围）、渲染一段"六关节逐个扫掠 + 协调正弦"的验证视频和静帧。
结构摘要样例见 `reports/`（随仓库提供）；对照视频（`media/`）体积较大，不随仓库分发——按上面的命令可随时重新生成。

## 三模型关键差异（实测）

| 项目 | 官方-新校准 | 官方-旧校准 | ROS2 描述包 |
| --- | --- | --- | --- |
| 零位语义 | 关节**行程中点** | 水平**完全伸展**位 | 行程中点 |
| 关节名 | `shoulder_pan` | 同左 | `shoulder_pan_joint`（后缀） |
| 位置增益 | kp=998.22, kv=2.731 | **kp=17.8, kv=0** | kp=998.22 |
| 夹爪单位 | 弧度 hinge | 弧度 hinge | **0~1 归一化** |
| 自碰撞排除 | 无 | 无 | 有（6 对） |

**跟踪误差实测**：新校准与描述包静止保持误差 0.0005 rad，旧校准 0.03 rad（下垂约 1.7°，kp 弱 56 倍）。
仿真里评估同一策略，换模型会得到不同动态，注意记录用的是哪一份。

## 必须记住的模型行为

1. **`shoulder_lift` 正方向朝下**：驱动力矩中"下摆"用正角度，做遥操映射或数据换算时先验符号。
2. **压地即挡**：下摆极限会让指尖接触地面并被挡停（脚本内置 8cm 离地保护自动裁幅）。
3. 官方模型无相机、无 keyframe；带相机的变体 `so101_new_calib_camera.xml` 存在，后续录视觉数据可用。

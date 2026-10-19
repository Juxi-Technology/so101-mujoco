# SO-ARM101 × MuJoCo 全流程教程（索引）

> 🌐 Languages: **简体中文** · [English](en/README.md) · [Deutsch](de/README.md) · [Español](es/README.md) · [Français](fr/README.md) · [Italiano](it/README.md) · [日本語](ja/README.md) · [한국어](ko/README.md) · [Português (BR)](pt-br/README.md) · [Português (PT)](pt-pt/README.md) · [繁體中文](zh-hant/README.md)

> 本教程记录并复现 SO-ARM101 的**仿真 + 真机完整工作流**：从环境搭建、模型验证、实机标定，
> 到键盘/主动臂遥操、数据录制与回放。所有命令均在 2026-10-15 的实机 + 仿真会话中实测通过。
>
> 适用对象：Juxi SO-ARM101 套件用户与内部工程师。不要求预先了解 MuJoCo 或 LeRobot。

## 全流程地图（两条轨，共用一套组件）

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

| 章 | 内容 | 你会得到 |
| --- | --- | --- |
| [01 环境准备](01-environment.md) | uv 环境、依赖 extras、Windows 注意事项 | 可运行的环境 |
| [02 仿真模型验证](02-sim-model-verification.md) | 三份 MJCF 模型加载/对比/驱动渲染 | 对模型与仿真行为的确信 |
| [03 实机连接与标定](03-hardware-calibration.md) | 串口识别、只读初检、从动臂/主动臂标定 | 可被软件识别的两台臂 |
| [04 键盘遥操](04-keyboard-teleop.md) | 键盘驱动真机/仿真、速率调参、安全限速 | 最快的手动控制方式 |
| [05 主动臂数字孪生](05-leader-digital-twin.md) | 实体主动臂驱动仿真从动臂、零点微调 | 数字孪生演示与数据采集 |
| [06 数据录制与回放](06-record-and-replay.md) | 录真机/录仿真/回合控制/回放/体检脚本 | 可训练的数据集 |
| [07 常见问题与经验](07-troubleshooting.md) | 本流程踩过的所有坑与解法 | 排障手册 |
| [08 后续路线](08-roadmap.md) | 相机、物体场景、自动数据生成、训练 | 下一步计划 |
| [09 完整使用教程](09-usage-tutorial.md) | 开臂 → 录制 → 体检 → 看视频 → 训练 → 仿真部署一条龙；含 conda 环境替代方案 | 从零到合格数据集，再到策略上场 |

## 三条必须记住的约定

1. **单位制（三方对齐）**：五个身体关节用 **−100~100**（行程比例，0 = 行程中点），夹爪用 **0~100**
   （0 = 闭合）。真机（`use_degrees=false`）、仿真、主动臂全部对齐这一约定；录出的数据集与官方
   `lerobot/svla_so101_pickplace` 等真机数据集结构一致（6 维向量 + 关节名）。
2. **角色对应**：被控对象（真机或仿真）永远配 `--robot.*`；操控设备（键盘/主动臂）永远配 `--teleop.*`。
3. **本机命令前缀**：这台开发机上所有 `uv` 命令需要先设缓存目录（原因见 [07](07-troubleshooting.md)）：

   ```bash
   export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
   ```

## 实测环境

| 项目 | 版本 |
| --- | --- |
| 系统 | Windows 11 |
| Python / uv | 3.12.9 / 0.12.5 |
| lerobot | 0.6.2（本仓库，项目 `.venv` 隔离，不影响 conda） |
| MuJoCo | 3.16.0 |
| PyTorch | 2.11.0（CPU 版） |
| 硬件 | SO-ARM101 主动臂（COM163）+ 从动臂（COM172），CH343 串口芯片 |

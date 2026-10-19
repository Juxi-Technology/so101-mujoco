# 01 · 环境准备

一次性操作。本仓库使用 **uv 管理一个项目内隔离的 `.venv`**——`uv run` 只会使用这个目录里的环境，
不会动你的 conda（这个设计是刻意的，见 [07 常见问题](07-troubleshooting.md)）。

## 安装

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'   # 本机特例，见 07

# CPU 版 torch（本机无独显；有 NVIDIA GPU 的机器去掉 UV_TORCH_BACKEND 并参考 pyproject 注释换 CUDA 版）
UV_TORCH_BACKEND=cpu uv sync --frozen --extra core_scripts --extra feetech --extra pynput-dep --extra training
```

四个 extra 的用途：

| extra | 提供什么 | 谁需要 |
| --- | --- | --- |
| `core_scripts` | 官方 record / teleoperate / calibrate / replay 入口 + 数据集 + 可视化依赖 | 全部 |
| `feetech` | `scservo_sdk`（STS3215 舵机串口协议） | 真机相关操作 |
| `pynput-dep` | 全局键盘监听 | 键盘遥操、录制回合控制键 |
| `training` | `accelerate` / `wandb` 等 | `lerobot-train` 训练、策略部署（`lerobot-rollout`） |

需要时再临时叠加 MuJoCo（不进锁定文件，按需加载）：

```bash
uv run --frozen --with mujoco python <脚本>
```

**想改用 conda 环境？**那运行命令就不需要 `uv run` 前缀了——建环境的三条命令与注意点见
[09 完整使用教程 · 附录 A](09-usage-tutorial.md)。

## 验证

```bash
uv run --frozen --with mujoco python -c "import mujoco, scservo_sdk, pynput, lerobot, torch; print('OK')"
uv run --frozen lerobot-calibrate --help | head -3   # 官方入口可用
```

## 常见问题

- **`uv sync` 报 `failed to persist temporary file ... os error 17`**：本机 uv 缓存目录跨盘的
  特例，用上面的 `UV_CACHE_DIR` 前缀即可，详见 [07](07-troubleshooting.md)。
- **不要用 Microsoft Store 版 Python**：选 uv 自动管理的 Python 3.12 即可。
- 首次 `uv run --with mujoco` 会下载约 5.6MB 的 mujoco wheel，之后走缓存。

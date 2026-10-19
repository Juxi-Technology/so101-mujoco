# 01 · Environment Setup

One-time setup. This repository uses **uv to manage a project-local, isolated `.venv`**—`uv run` only uses the environment in that directory and
never touches your conda (this design is deliberate; see [07 Troubleshooting](07-troubleshooting.md)).

## Installation

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'   # 本机特例，见 07

# CPU 版 torch（本机无独显；有 NVIDIA GPU 的机器去掉 UV_TORCH_BACKEND 并参考 pyproject 注释换 CUDA 版）
UV_TORCH_BACKEND=cpu uv sync --frozen --extra core_scripts --extra feetech --extra pynput-dep --extra training
```

What the four extras provide:

| extra | What it provides | Who needs it |
| --- | --- | --- |
| `core_scripts` | Official record / teleoperate / calibrate / replay entry points + dataset + visualization dependencies | Everyone |
| `feetech` | `scservo_sdk` (STS3215 servo serial protocol) | Real-hardware operations |
| `pynput-dep` | Global keyboard listener | Keyboard teleoperation, recording episode-control keys |
| `training` | `accelerate` / `wandb`, etc. | `lerobot-train` training, policy deployment (`lerobot-rollout`) |

Add MuJoCo on demand when needed (it is not in the lock file; it is loaded per invocation):

```bash
uv run --frozen --with mujoco python <脚本>
```

**Prefer to use a conda environment instead?** Then the run commands no longer need the `uv run` prefix—see
[09 Complete Usage Tutorial · Appendix A](09-usage-tutorial.md) for the three environment-creation commands and caveats.

## Verification

```bash
uv run --frozen --with mujoco python -c "import mujoco, scservo_sdk, pynput, lerobot, torch; print('OK')"
uv run --frozen lerobot-calibrate --help | head -3   # 官方入口可用
```

## Common Issues

- **`uv sync` reports `failed to persist temporary file ... os error 17`**: a quirk of this machine where the uv cache directory is on a different
  drive; prepend the `UV_CACHE_DIR` setting above. See [07](07-troubleshooting.md) for details.
- **Do not use the Microsoft Store version of Python**: just use the Python 3.12 managed automatically by uv.
- The first `uv run --with mujoco` downloads the roughly 5.6 MB mujoco wheel; subsequent runs use the cache.

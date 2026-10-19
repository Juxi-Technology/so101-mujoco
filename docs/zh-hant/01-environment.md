# 01 · 環境準備

一次性操作。本儲存庫使用 **uv 管理一個專案內隔離的 `.venv`**——`uv run` 只會使用這個目錄裡的環境，
不會動到你的 conda（這個設計是刻意的，見 [07 常見問題](07-troubleshooting.md)）。

## 安裝

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'   # 本机特例，见 07

# CPU 版 torch（本机无独显；有 NVIDIA GPU 的机器去掉 UV_TORCH_BACKEND 并参考 pyproject 注释换 CUDA 版）
UV_TORCH_BACKEND=cpu uv sync --frozen --extra core_scripts --extra feetech --extra pynput-dep --extra training
```

四個 extra 的用途：

| extra | 提供什麼 | 誰需要 |
| --- | --- | --- |
| `core_scripts` | 官方 record / teleoperate / calibrate / replay 入口 + 資料集 + 視覺化相依套件 | 全部 |
| `feetech` | `scservo_sdk`（STS3215 伺服馬達序列埠協定） | 實機相關操作 |
| `pynput-dep` | 全域鍵盤監聽 | 鍵盤遙控操作、錄製回合控制鍵 |
| `training` | `accelerate` / `wandb` 等 | `lerobot-train` 訓練、策略部署（`lerobot-rollout`） |

需要時再臨時疊加 MuJoCo（不列入鎖定檔，按需載入）：

```bash
uv run --frozen --with mujoco python <脚本>
```

**想改用 conda 環境？**那麼執行指令就不需要 `uv run` 前綴了——建立環境的三條指令與注意事項見
[09 完整使用教學 · 附錄 A](09-usage-tutorial.md)。

## 驗證

```bash
uv run --frozen --with mujoco python -c "import mujoco, scservo_sdk, pynput, lerobot, torch; print('OK')"
uv run --frozen lerobot-calibrate --help | head -3   # 官方入口可用
```

## 常見問題

- **`uv sync` 顯示 `failed to persist temporary file ... os error 17`**：本機 uv 快取目錄跨磁碟的
  特例，使用上面的 `UV_CACHE_DIR` 前綴即可，詳見 [07](07-troubleshooting.md)。
- **不要使用 Microsoft Store 版 Python**：選擇由 uv 自動管理的 Python 3.12 即可。
- 首次 `uv run --with mujoco` 會下載約 5.6MB 的 mujoco wheel，之後會走快取。

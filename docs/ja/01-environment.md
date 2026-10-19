# 01 · 環境準備

一度だけの作業です。本リポジトリは **uv でプロジェクト内に分離した `.venv` を管理**します——`uv run` はこのディレクトリ内の環境だけを使い、
あなたの conda には触れません（この設計は意図的です。[07 よくある問題](07-troubleshooting.md) を参照）。

## インストール

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'   # 本机特例，见 07

# CPU 版 torch（本机无独显；有 NVIDIA GPU 的机器去掉 UV_TORCH_BACKEND 并参考 pyproject 注释换 CUDA 版）
UV_TORCH_BACKEND=cpu uv sync --frozen --extra core_scripts --extra feetech --extra pynput-dep --extra training
```

4 つの extra の用途：

| extra | 提供するもの | 必要な人 |
| --- | --- | --- |
| `core_scripts` | 公式 record / teleoperate / calibrate / replay エントリ + データセット + 可視化依存 | 全員 |
| `feetech` | `scservo_sdk`（STS3215 サーボのシリアルプロトコル） | 実機関連の操作 |
| `pynput-dep` | グローバルキーボードリスニング | キーボード遠隔操作、録画のエピソード制御キー |
| `training` | `accelerate` / `wandb` など | `lerobot-train` による学習、ポリシー展開（`lerobot-rollout`） |

必要時に MuJoCo を一時的に重ねて使う（ロックファイルには含めず、必要時ロード）：

```bash
uv run --frozen --with mujoco python <脚本>
```

**conda 環境に切り替えたい場合**は、実行コマンドに `uv run` プレフィックスが不要になります——環境構築の 3 コマンドと注意点は
[09 完全使用チュートリアル · 付録 A](09-usage-tutorial.md) を参照してください。

## 検証

```bash
uv run --frozen --with mujoco python -c "import mujoco, scservo_sdk, pynput, lerobot, torch; print('OK')"
uv run --frozen lerobot-calibrate --help | head -3   # 官方入口可用
```

## よくある問題

- **`uv sync` が `failed to persist temporary file ... os error 17` を報告**：本機の uv キャッシュディレクトリがドライブをまたぐ
  特殊事情です。上記の `UV_CACHE_DIR` プレフィックスを使えば解決します。詳細は [07](07-troubleshooting.md)。
- **Microsoft Store 版 Python を使わない**：uv が自動管理する Python 3.12 を選べば問題ありません。
- 初回の `uv run --with mujoco` は約 5.6MB の mujoco wheel をダウンロードし、以後はキャッシュを使います。

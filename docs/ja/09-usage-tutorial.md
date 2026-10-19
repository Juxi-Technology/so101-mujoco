# 09 · 完全使用チュートリアル（アーム起動 → データセット → 動画確認 → 学習 → 展開）

> 一気通貫の操作マニュアル：一度たどれば、「リーダーアームを挿す」ところから「学習済みポリシーがシミュレーションで自律的に働く」ところまで到達できます。
> 前提：環境は [01](01-environment.md) に従って構築済み、リーダーアームは [03](03-hardware-calibration.md) に従ってキャリブレーション済み
> （本機は `juxi_leader` / COM124）。録画関連の落とし穴は [07](07-troubleshooting.md) に集約しています。

## 0 · 一度だけの準備

```bash
# 本机所有 uv 命令都要先设（跨盘缓存特例，见 07）
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
```

リーダーアームを挿し、シリアルポートを確認（**抜き差しのたびに番号が変わることがあります**）：

```bash
uv run --frozen python -c "from serial.tools import list_ports; print([p.device for p in list_ports.comports()])"
```

デスクトップにスペースを空けてください：録画では **3 つのウィンドウ**（メインビュー + `wrist camera - live` + `top camera - live`）が開きます。

## 1 · 遠隔操作でウォームアップ（推奨）

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_mujoco \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader \
    --teleop.use_degrees=false
```

リーダーアームを動かしてみて、シミュレーションアームが追従することを確認；終了（Ctrl-C）前にリーダーアームを**中位姿勢付近**に止めておくと、録画開始瞬間に大きな収束区間が出ません。

## 2 · 録画（中核コマンド）

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/record.py \
    --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader \
    --teleop.use_degrees=false \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision \
    --dataset.num_episodes=5 --dataset.episode_time_s=600 --dataset.reset_time_s=10 \
    --dataset.single_task="put the cube in the box" \
    --dataset.video=true --dataset.push_to_hub=false --play_sounds=false --dataset.no_stamp=true
```

要点（その他のパラメータは [06](06-record-and-replay.md) のパラメータ表を参照）：

| 項目 | 説明 |
| --- | --- |
| `--dataset.root` | **root はデータセットディレクトリそのもの**、録画ごとに新しいディレクトリに変える（同名ディレクトリが存在すると起動を拒否） |
| 自動注入されるデフォルト値 | 動画エンコード `h264`、エンコードスレッド `2`——`record.py` は起動時に 2 行のヒントを表示；明示的に `--dataset.rgb_encoder.vcodec=...` / `--dataset.encoder_threads=...` を渡せば上書き可能（理由は 07 参照） |
| プレビューウィンドウ | デフォルトで有効（15Hz、`--robot.preview_cameras=false` で無効化；`--robot.preview_fps` で調整可能） |
| `--dataset.video=true` | デュアルカメラ映像を保存（`observation.images.wrist / top`）；手首カメラだけなら `top_camera` を外す |

## 3 · 録画中の操作

| キー | 作用 |
| --- | --- |
| `→` または `n` | 現在のエピソードを終了して保存 |
| `←` または `r` | 現在のエピソードを破棄し、その場で録り直し |
| `q` | セッション全体を終了し、データセットを保存 |

- エピソード終了後は**ブロックが自動的に元の位置に戻る**ので、リーダーアームを開始姿勢に戻すだけでよい；`Recording episode N` が表示されてから次のエピソードの動作を始める。
- 保存段階（数十秒）ではコンソールに `[record.py] reset done; saving the episode + encoding videos now` が表示される——
  この間は**キー入力は安全に無視される**（誤押しでどのエピソードも壊れない）。次の行 `Recording episode` が表示されてから操作する。
- エンコード失敗には**自動リトライのフォールバック**あり（`video encode failed ... retrying once` を表示後、3 秒で自動リトライ）；保存済みのエピソードは決して失われない。

## 4 · 検査

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

出力の読み方：

- **action span がすべて 0（またはグリッパが 0）のエピソード**は空録画／無効録画、削除して録り直し；
- **各エピソード冒頭の `max |act-obs|` が大きい**のは収束区間で正常；中盤以降は ~10 単位未満であるべき。

## 5 · 動画を見る

```bash
uv run --frozen python examples/so101_mujoco/export_videos.py \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

成果物：

- `examples/so101_mujoco/outputs/videos/<数据集名>/epN_top.mp4`、`epN_wrist.mp4` —— **エピソードごと・カメラごとに 1 本のダブルクリック再生可能な動画**；
- `examples/so101_mujoco/outputs/renders/<数据集名>_epN_dual.png` —— エピソードごとに 1 枚の合成画像（上段が俯瞰、下段が手首、6 フレームを均等サンプリング）、素早い目視チェック用（`--no-strips` でスキップ可能）。

データセット内にも元のパッケージ動画（複数エピソードを順番に 1 ファイルへ連結）があります：
`outputs/datasets/<数据集名>/videos/observation.images.{top,wrist}/chunk-000/file-000.mp4`。

## 6 · 再生（任意）

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision --dataset.episode=0
```

## 7 · 学習

```bash
uv run --frozen lerobot-train \
    --policy.type=act \
    --policy.push_to_hub=false \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision \
    --output_dir=examples/so101_mujoco/outputs/train/act_so101_sim_vision \
    --steps=100000 --batch_size=8 --save_freq=20000 --log_freq=200 \
    --num_workers=4 --wandb.enable=false --policy.device=cpu
```

| 要点 | 説明 |
| --- | --- |
| `--policy.type` | ポリシータイプ、**`act` から始める**（このデータ規模／タスクに最適）；`ls src/lerobot/policies/` で他の選択肢（diffusion / smolvla / pi0 など）を確認できる |
| `--policy.push_to_hub=false` | **必ず追加**——デフォルトでは HuggingFace Hub へプッシュしようとし、`repo_id` 未設定だと直接エラー終了する；プッシュする場合は `--policy.repo_id=你的用户名/模型名` に変更（事前に `hf auth login` が必要） |
| `--policy.device=cpu` | 本機は GPU なしのため `cpu`；NVIDIA カード搭載機ではこのパラメータを削除（自動で cuda 使用） |
| 成果物 | `output_dir/checkpoints/<步数>/` と `checkpoints/last/pretrained_model/`——展開時は後者を指定；継続学習用の `train_config.json` もその中にある |
| 継続学習 | 中断後、元のコマンドに追加：`--resume=true --config_path=<output_dir>/checkpoints/last/pretrained_model/train_config.json` |

**本機の速度見込み**：純 CPU で約 **2 秒/ステップ**（batch 2、480p デュアルカメラ；実測 12 ステップのスモークで loss が 70 から 22 に低下、方向は正常）。
そのため本機は小ステップ数でのパイプライン検証向き——チュートリアル同梱の `outputs/train/smoke_act` はまさに 12 ステップの成果物；
**正式学習（ACT は通常 10 万ステップ規模）は GPU 搭載機への変更を推奨、コマンドは完全に同じ。**

> 依存関係のヒント：学習には `training` extra（accelerate など）が必要。`accelerate is required but not installed` と表示されたら、
> [01](01-environment.md) のインストールコマンドに `--extra training` を追加して再試行してください。

## 8 · 展開（ポリシーにシミュレーションで自律的に働かせる）

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/rollout.py \
    --policy.path=examples/so101_mujoco/outputs/train/act_so101_sim_vision/checkpoints/last/pretrained_model \
    --strategy.type=base \
    --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --task="put the cube in the box" --duration=30
```

| 要点 | 説明 |
| --- | --- |
| カメラパラメータ | `--robot.image_camera/--robot.top_camera` は**録画データセット時と一致必須**（sim_cam + top_cam）。そうしないとポリシーは学習時に見た映像を得られない |
| `--task` | 録画時の `--dataset.single_task` と一致させる |
| `--duration` | 何秒走ったら自動終了するか（終了前にアームを初期姿勢へ戻してから切断）；途中で `Ctrl-C` でも停止可能 |
| まずパイプラインを試したい | チュートリアル同梱のデモモデルでよい：`--policy.path=examples/so101_mujoco/outputs/train/smoke_act/checkpoints/last/pretrained_model`（12 ステップ学習、動作はほぼでたらめ、パイプライン検証のみ） |
| 純 CPU 展開 | ポリシー推論で 0.5s のスパイクが偶発し、`Control loop is running slower ... than the target FPS` が表示される——シミュレーションでは動くがカクつく；GPU ではこの問題なし（実測 20s スモークは全編動作、正常終了） |
| 実機展開 | `--robot.*` を実機に置き換え：`--robot.type=so101_follower --robot.port=COMxx --robot.id=juxi_so101 --robot.use_degrees=false`（デスクトップにスペースを空けること） |
| その他のモード | `--strategy.type=sentry / highlight / dagger / episodic`：実行しながら録画 / リングバッファでキー保存 / ヒューマンインザループで修正 / エピソード単位の録画、`lerobot-rollout --help` 参照 |

## 付録 A · conda 環境に切り替える（任意）

本リポジトリはデフォルトで **uv 管理のプロジェクト内 `.venv`** を使い（[01](01-environment.md) 参照）、実行コマンドにはすべて
`uv run --frozen --with mujoco` プレフィックスが必要です。conda に慣れている場合は、**「環境構築」のステップを次の 3 コマンドに置き換え**、
その後**すべてのコマンドから uv プレフィックスを外します**（`python examples/...` で直接実行）。`UV_CACHE_DIR` も不要になります
（これは uv のドライブ間キャッシュの特殊事情で、conda とは無関係）：

```bash
# 一次性：在仓库根目录建好环境（python 版本对齐 01 的 3.12）
conda create -n lerobot-sim python=3.12 -y
conda activate lerobot-sim
pip install -e .            # 安装本仓库 lerobot 及其依赖（含 torch，Windows 上 pip 默认就是 CPU 版）
pip install "mujoco==3.16"  # uv 路线用 --with mujoco 临时提供，conda 路线装成常驻依赖
```

その後、例えば録画はこうなります：

```bash
python examples/so101_mujoco/record.py --robot.image_camera=sim_cam ...
```

2 つの注意点：

1. **バージョン整合**：`pip install -e .` は pip が独自にバージョンを解決するため、`uv.lock` と完全に一致するとは限らない；
   現在の実測環境と一字一句同じ組み合わせが欲しい場合は、uv で conda 環境へロックファイルどおりにインストールする：

   ```bash
   uv pip sync uv.lock --python "$(conda run -n lerobot-sim python -c 'import sys; print(sys.executable)')"
   pip install "mujoco==3.16"
   ```

2. リーダーアームのキャリブレーションキャッシュは `~/.cache/huggingface/lerobot/calibration/` にあり、どの環境を使うかとは無関係なので、環境を移行しても再キャリブレーションは不要。

## 付録 B · よくある落とし穴早見表

| 現象 | 一言で |
| --- | --- |
| シリアルポートが開けない | まずポートを列挙、番号が変わっているかも（ステップ 0） |
| 保存時にコンソールが数十秒静か | エンコード中で正常；`saving the episode...` のヒントが見えたらキーを押さない |
| 録画中に画面がときどきカクつく | 保存ウィンドウのエンコード資源競合；制御ループ自体は影響を受けない（cadence の数値基準）、詳細は 07 |
| 一度クラッシュしても救えるか | 保存済みエピソードは決して失われない；`record.py --resume=true ... --dataset.num_episodes=N` で続きを録画 |
| `lerobot-train` が `'repo_id' argument missing` を報告 | デフォルトで Hub にプッシュしようとする：`--policy.push_to_hub=false` を追加（プッシュするなら `--policy.repo_id` を設定し先に `hf auth login`） |
| 展開時にポリシーが動かない／でたらめに動く | まず `--robot.image_camera/--robot.top_camera` と `--task` が録画時と一致するか確認；次に学習ステップ数が少なすぎないか確認 |

すべての落とし穴と解決策（メモリ逼迫、エンコード OOM、空エピソードなど）は [07 · よくある問題](07-troubleshooting.md) 参照。

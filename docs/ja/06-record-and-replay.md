# 06 · データ録画と再生

## 録画コマンドテンプレート

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'

# 录真机（主动臂 → 真机从动臂）
uv run --frozen --with mujoco python examples/so101_mujoco/record.py \
    --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101 \
    --robot.use_degrees=false --robot.max_relative_target=10 \
    --teleop.type=so101_leader_trim --teleop.port=COM163 --teleop.id=juxi_leader \
    --teleop.use_degrees=false \
    --dataset.repo_id=local/juxi_so101_teleop \
    --dataset.root=examples/so101_mujoco/outputs/datasets/real_run1 \
    --dataset.num_episodes=5 --dataset.episode_time_s=600 --dataset.reset_time_s=10 \
    --dataset.single_task="pick up the cube" \
    --dataset.video=false --dataset.push_to_hub=false --play_sounds=false --dataset.no_stamp=true

# 录仿真（主动臂 → 仿真从动臂）
#   把 --robot.* 换成: --robot.type=so101_mujoco
# 录仿真（键盘控制）
#   把 --teleop.* 换成: --teleop.type=so101_keyboard --teleop.rate=150
```

## パラメータの要点（ハマりやすいところ）

| パラメータ | 説明 |
| --- | --- |
| `--dataset.root` | **root はデータセットディレクトリそのもの**（親ディレクトリ + repo_id の結合ではない）；録画ごとに新しいディレクトリに変える |
| `--dataset.repo_id` | ローカル録画では単なる識別子；将来 Hub にプッシュするときに初めて実際の `用户名/名字` が必要 |
| `--dataset.no_stamp=true` | タイムスタンプ接尾辞を付けず、ディレクトリ／名前を安定させる；同名で録り直す場合は先に旧ディレクトリを削除 |
| `--dataset.episode_time_s` | 1 エピソードの**上限**（保険）；通常操作では `→` で早めに終了 |
| `--dataset.reset_time_s` | エピソード間の記録しないリセット時間；この間もリーダーアームはリアルタイムでフォロワーアームを駆動。**シミュレーション録画ではこの段階に入るとブロックが自動的に初期位置へテレポートします**（下記参照） |
| `--dataset.video` | カメラデータが必要なときだけ有効化（視覚データセットは true 必須；pyav フォールバックは動作確認済み） |
| `--dataset.rgb_encoder.vcodec` | 動画エンコーダ。**本機のデュアルカメラ録画では `h264`**：`record.py` がデフォルトで注入済み（上流デフォルトの libsvtav1 は 2 路のエンコードを同時に開くとメモリ割り当てに失敗し、セッション全体がクラッシュ——[07](07-troubleshooting.md) 参照）；明示的に渡した場合は注入されない |
| `--dataset.encoder_threads` | エンコードスレッド数。**`record.py` のデフォルトは 2 を注入**：デフォルトで全コアを使い切ると保存中のシミュレーション画面が明らかにカクつく（[07](07-troubleshooting.md) 参照）；各エンコードを 2 スレッドに制限すると保存中もシミュレーションが滑らかに保たれる；明示的に渡した場合は注入されない |
| `--dataset.push_to_hub` | 本機から HF へ直接接続するにはプロキシが必要なので、まず false のままにし、録画後に手動でプッシュ |

## エピソード制御キー（グローバル、録画中は常に有効）

| キー | 作用 |
| --- | --- |
| `→` または `n` | 現在のエピソードを終了（**保存**） |
| `←` または `r` | 現在のエピソードを破棄し**その場で録り直し**（1 エピソードが不満なときに使い、セッションを再起動しなくてよい） |
| `q` | セッション全体を終了し、データセットを保存（**推奨**） |
| `Esc` | `q` と同じ（キーボード遠隔操作も切断される；クリーン終了は確認済みだが、やはり `q` を優先） |

**操作の推奨**：録画開始前にリーダーアームを中位姿勢付近に止めておく（開始瞬間にシミュレーションアーム／実機アームが「振り切れる」収束区間が録画に入るのを避ける）；
開始後はまず 1 秒静止してから動作を始めてください。

## シミュレーション録画の自動シーンリセット

実機録画では「Reset the environment」段階でブロックを手動で元の位置に戻す必要があります。シミュレーションでは録画ランチャー（`record.py`）
がこの段階の開始時に**3 つのブロックを自動的にスポーン位置へテレポート**（同時に速度をゼロに）するため、各エピソードで `→` を押して終了した後は、
リーダーアームを初期姿勢に戻すだけでブロックは自動的に元に戻り、次のエピソードは固定の初期シーンから始まります。
実機フォロワーアームにはこの挙動はありません（従来どおり手動で配置）；`teleoperate.py`/`replay.py` も関与しません。

## 録画後の検査

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

各エピソードのフレーム数、時間、6 関節の動作振幅と追従誤差を出力します：

- **action span = 0 のエピソード**は空録画（人が動いていない）なので、削除して録り直せばよい；
- **冒頭の |action−obs| が大きい**のは収束区間（正常）、中盤以降は通常 <10 単位。

## シミュレーションで「映像付き」データを録る（wrist カメラ）

シミュレーションロボットはシーン内の手首カメラ（`sim_cam`）を画像観測としてデータセットに録画できます：

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/record.py \
    --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader \
    --teleop.use_degrees=false \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision \
    --dataset.num_episodes=5 --dataset.episode_time_s=600 --dataset.reset_time_s=10 \
    --dataset.single_task="pick up the cube" \
    --dataset.video=true --dataset.push_to_hub=false --play_sounds=false --dataset.no_stamp=true
```

要点：`--robot.image_camera=sim_cam`（カメラ名）+ `--dataset.video=true`（画像は動画エンコードを通す、pyav フォールバックは動作確認済み）。
データセットの特徴量に `observation.images.wrist`（480×640×3）が現れます。解像度とフレームレートは
`--robot.image_width/--robot.image_height/--robot.image_fps` で調整できます。
ウィンドウを開く場合（`onscreen=true`、デフォルト）、メインビューのウィンドウに加えて**カメラごとにリアルタイムプレビューウィンドウが 1 つずつ**
開きます（手首／俯瞰、ウィンドウ左上にラベルあり）。録画中に 2 路の映像が正常かを直接確認できます；不要なら
`--robot.preview_cameras=false` を追加してください。プレビューウィンドウはデフォルトで **15Hz** 更新（`--robot.preview_fps` で調整可能）——
これらは状態表示であり、メインウィンドウの 50Hz に追従する必要はないため、同じ画面に 3 つのウィンドウがあってもレンダリング負荷がはるかに小さくなります。

**シーンと俯瞰カメラ（2026-10-16 以降）**：シミュレーションシーンにはワークスペースが組み込まれています——マット、3 色のブロック（34mm）、収納ボックス（`so101_assets.add_workspace` 参照、
レイアウトは `preview_workspace.py` でレンダリングして微調整可能）；さらに固定の俯瞰カメラ `top_cam` があります（画面の上方向 = ロボットアームから遠ざかる方向）。
`--robot.top_camera=top_cam` を追加すると俯瞰映像が `observation.images.top` として録画されます（2 カメラ同時録画）；手首カメラだけならこのパラメータを外してください。
1 エピソード終了後の動画エンコードは 2 路の映像を同時に処理するため、待ち時間がやや長くなるのは正常です。

## 再生

```bash
# 仿真空回放（窗口里看轨迹重演）
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision --dataset.episode=0

# 真机回放（同款机制，注意周围环境与录制时一致）
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101 \
    --robot.use_degrees=false --robot.max_relative_target=10 \
    --dataset.repo_id=local/juxi_so101_teleop \
    --dataset.root=examples/so101_mujoco/outputs/datasets/juxi_teleop_run1 --dataset.episode=0
```

> 公式の `lerobot-replay` エントリは本プロジェクトのプラグインをロードしないため、そのまま使うと `invalid choice: 'so101_mujoco'` が発生します——
> そのため一律で `replay.py` ランチャー経由で実行します。

## データセット形式と場所

データセットは LeRobotDataset v3：`action` と `observation.state` はいずれも 6 次元ベクトル
（`shoulder_pan.pos … gripper.pos`）で、公式の実機データセットと一致し、そのまま混合学習できます。

```
examples/so101_mujoco/outputs/datasets/
└── juxi_teleop_run1/   真机键盘遥操（1 回合 / 2430 帧 / 81s）✅ 保留的真机数据

> 2026-10-16 清理：旧的仿真录制（`sim_run2`、`sim_vision_demo`、`sim_vision_run1/2/3`）
> 已全部删除。**正式数据集 `so101_sim_vision`（双相机 / 5 回合 / 10610 帧 / 353.8s / h264）
> 已于当晚录成 ✅**；每回合单机视频导出在 `outputs/videos/so101_sim_vision/`，
> 双相机预览拼图在 `outputs/renders/sim_vision_epN_dual.png`。
```

## 今回の実測記録（2026-10-15）

| セッション | 内容 | 結果 |
| --- | --- | --- |
| 実機 run1 | キーボード遠隔操作で実機を録画 | 1 エピソード 81s、6 関節の振幅 75〜140 単位、30Hz で安定 |
| 実機再生 | 同エピソードを再生 | 2430 フレームを完全再現、異常なし |
| シミュレーション run2 | リーダーアームでシミュレーションを録画 | 5 エピソード 157s、ep1〜4 の追従誤差 <12 単位 |
| シミュレーション再生 ep1 | ウィンドウで再演 | 軌跡は操作と一致（確認済み） |

## 追加実測（2026-10-16）

| セッション | 内容 | 結果 |
| --- | --- | --- |
| 新しいリーダーアーム（COM124） | 再キャリブレーション（新アーム／新サーボ）| ✅ キャリブレーション成功；`so101_leader_trim` のゼロ点補償は新しいキャリブレーションに自動適応 |
| 視覚 run1 | リーダーアームでシミュレーションを録画（映像付き）| 2 エピソード / 3177 フレーム / 106s @ 29.97Hz；追従誤差は全編 ≤2 単位（初回フレームの収束 0.5s のみ）；`observation.images.wrist` 動画をデータセットに保存しデコード検証済み ✅ |
| 視覚 run2 | デュアルカメラで続き録画（`--resume`）| ep0（2776 フレーム / 92.6s）は無損失；ep1 保存時に libsvtav1 エンコーダが OOM でセッション全体がクラッシュ → エンコーダを h264 に変更（`record.py` がデフォルト注入）しエンドツーエンドで実測通過（2 エピソード × 2 路エンコード）；残留を整理し、正式録画は run3 へ |
| 視覚 run3 | デュアルカメラ正式録画（h264）| 第 1 セッション：ep0（185.2s / 5554 フレーム）+ ep1（72.8s / 2186 フレーム）が無傷で保存され検査通過；セッション間のエンコード停止中に `→` を連打して空エピソードクラッシュを誘発（メカニズムと対策は [07](07-troubleshooting.md)）→ 続きのセッションで残りエピソードを録画（5 エピソード計画）|
| 正式録画初戦（so101_sim_vision）| デュアルカメラ（h264 + 2 スレッド + プレビューウィンドウ 15Hz）| ep0（82.3s / 2469 フレーム）保存時にエンコーダのメモリ割り当て失敗でセッション全体がクラッシュ（システム commit がほぼ満杯、[07](07-troubleshooting.md) 参照）→ **エンコード失敗時の自動リトライ**と**コンソール静音化**を追加（いずれも実測有効、スモーク 26 項目すべて通過）；マシン再起動後に正式録画予定 |
| 正式録画（so101_sim_vision）✅ | デュアルカメラのリーダーアーム遠隔操作、5 エピソード | **5/5 エピソードすべて保存**：61.5 / 53.4 / 101.1 / 62.4 / 75.4 s、計 10610 フレーム @29.97Hz、0 tick 予算超過、クラッシュゼロ；6 軸+グリッパ全編で有効な動作；2 路動画のデコード検証通過 |

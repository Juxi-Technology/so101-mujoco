# 04 · キーボード遠隔操作

キーボードで関節を「点動」させ、実機またはシミュレーションのアームを手動制御します——リーダーアームが不要なときの最速の制御方法であり、デモデータを録画する手段の 1 つでもあります。

## コマンド

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'

# 真机从动臂
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101 \
    --robot.use_degrees=false --robot.max_relative_target=5 \
    --teleop.type=so101_keyboard --teleop.rate=150

# 仿真从动臂（MuJoCo 窗口自动打开）
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --teleop.rate=150
```

（`teleoperate.py` はデフォルトで `--robot.type=so101_mujoco --teleop.type=so101_keyboard` です。）

## キー（押している間有効、グローバルリスニング——ウィンドウのフォーカスはどこでも可）

| キー | 動作 | キー | 動作 |
| --- | --- | --- | --- |
| `w` / `s` | shoulder_lift 上 / 下 | `a` / `z` | shoulder_pan 左 / 右 |
| `e` / `d` | elbow_flex 伸 / 屈 | `t` / `g` | wrist_flex + / − |
| `y` / `h` | wrist_roll + / − | `u` / `j` | グリッパ 開く / 閉じる |

キーは**録画制御キー（`n/r/q`、矢印キー、`Esc`）を意図的に避けて**選ばれており、遠隔操作と録画を同時に走らせられます。

## 主要パラメータ

| パラメータ | 役割 | 推奨値 |
| --- | --- | --- |
| `--teleop.rate` | キーを押している間の目標速度（単位/秒） | デフォルト 60 はやや遅い；実機の操作感は **150** が適切 |
| `--robot.max_relative_target` | 制御周期ごとに関節を動かす最大単位（安全速度制限） | 実機 **5**（60Hz 遠隔操作）/ **10**（30Hz 録画） |
| `--robot.use_degrees=false` | 角度制ではなくストローク比率制（−100〜100）を使う | **実機では必須**。そうしないと単位が合わない（シミュレーションはデフォルトで一致） |

## 挙動の説明

- **遠隔操作中はタイピングしないでください**：キーボードリスニングは**グローバルで、キーを消費しません**——コンピュータ上のどのウィンドウでマッピングキー
  （`w a s z e d t g y h u j`、チャット欄のピンイン入力も含む）を叩いてもアームが同時に動きます。リーダーアームモードではこの問題はありません。
- **接続の瞬間にアームが動きます**：実機のフォロワーアームはまずトルクが入り（硬くなり）、その後「中点姿勢」へ移動します（キーを押す前の目標）；
  シミュレーションのアームは直接中点姿勢に収束します。手元にスペースを空けておいてください。
- **終了**：そのターミナルで `Ctrl-C`（または `Esc` を押すとキーボードリスニングが切断されクリーンに終了）。終了後、実機は**トルクが切れて柔らかくなる**ので、
  手で支えてください——これは正常な動作です。
- **起動ログに連続する `clamped to be safe` WARNING** は速度リミッタが「追いつく」ときの正常な出力で、到達すると自動的に止まります。

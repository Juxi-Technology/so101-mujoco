# 03 · 実機接続とキャリブレーション

## シリアルポートの特定

CH343 チップのドライバボードを挿すと COM ポートが 1 つ現れます。**番号は抜き差しや USB ポートの変更で変わります**。接続前に毎回確認してください：

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen python -c "import serial.tools.list_ports as lp; [print(p.device, '|', p.description, '|', p.hwid) for p in lp.comports()]"
```

## ステップ 1：読み取り専用の初期チェック（配線／給電／サーボ点検）

**何も書き込まず**、まず 6 つのサーボを 1 つずつ ping してから電圧と温度を読みます（トルク状態はそのまま保持）：

```bash
uv run --frozen python examples/so101_mujoco/hardware_check.py --port COM163
```

正常な出力は次のような形です：6 行の関節、温度 20〜30°C、トルク 0（アームは自由）。**電圧は給電方式によります**：フォロワーアームを外部
電源に接続した場合は約 11V、リーダーアームをドライバボードからの給電のみにした場合は約 5V——6 つのサーボすべてを読み取れれば配線は正常です。欠落や型番不一致が
あれば直接エラーになります。

## ステップ 2：キャリブレーション

キャリブレーションは「各関節のストローク範囲 + 中点リファレンス」をサーボの EEPROM に書き込み、ローカルファイルに保存します。**フォロワーアームとリーダーアームはそれぞれ 1 回ずつ**行う必要があります。
2 台のアームのキャリブレーションファイルは別々に保存され、互いに影響しません：

| デバイス | コマンド | キャリブレーションファイルの保存先 |
| --- | --- | --- |
| フォロワーアーム | `uv run --frozen lerobot-calibrate --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101` | `~/.cache/huggingface/lerobot/calibration/robots/so_follower/juxi_so101.json` |
| リーダーアーム | `uv run --frozen lerobot-calibrate --teleop.type=so101_leader --teleop.port=COM163 --teleop.id=juxi_leader` | `.../calibration/teleoperators/so_leader/juxi_leader.json` |

`id` は任意の名前で構いませんが、**以降の遠隔操作／録画では必ず同じ id を使ってください**。そうしないと再度キャリブレーションを促されます。

### 物理手順（ターミナルに模式図が表示されます）

1. **中位姿勢に合わせて Enter**：ベースを机の端に平置きし、上腕を垂直上向き、前腕を水平前方、肩の回転と手首を中央に
   （リーダーアームの「グリッパ」はハンドル／トリガー）。この瞬間の位置がそのアームの「中点リファレンス」として記録されます。
2. Enter 後、**各関節を 1 つずつゆっくりと可動範囲全体に動かし**（`wrist_roll` はスイープ不要、自動で全周扱い）、再度 Enter で保存します。

注意事項：

- フォロワーアームはキャリブレーション中トルクが 0（アームは柔らかい）なので、手で支えながら動かします。リーダーアームは元々トルクがありません。
- キャリブレーション中はサーボに EEPROM を書き込みます（これはキャリブレーションの一部であり正常です）。
- 今回の実測キャリブレーション結果（比較用）：フォロワーアームの各関節ストローク 1474〜2688 カウント、`wrist_roll` 4095；
  リーダーアーム 2208〜2681 カウント。ストロークが明らかに非対称なのは正常です（[05 ゼロ点微調整](05-leader-digital-twin.md) でなぜ必要かを説明）。

# 09 · 完整使用教學（開臂 → 資料集 → 看影片 → 訓練 → 部署）

> 一條龍操作手冊：照著走一遍，就能從「插上主動臂」一路走到「訓練好的策略自己在模擬中幹活」。
> 前提：環境已依 [01](01-environment.md) 安裝完成、主動臂已依 [03](03-hardware-calibration.md) 校正
> （本機為 `juxi_leader` / COM124）。所有錄製相關的坑都集中在 [07](07-troubleshooting.md)。

## 0 · 一次性準備

```bash
# 本机所有 uv 命令都要先设（跨盘缓存特例，见 07）
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
```

插上主動臂，確認序列埠（**每次插拔都可能改變編號**）：

```bash
uv run --frozen python -c "from serial.tools import list_ports; print([p.device for p in list_ports.comports()])"
```

桌面留出空間：錄製會彈出 **3 個視窗**（主視角 + `wrist camera - live` + `top camera - live`）。

## 1 · 遙控操作暖身（推薦）

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_mujoco \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader \
    --teleop.use_degrees=false
```

動一動主動臂，確認模擬臂跟手；結束（Ctrl-C）前將主動臂停到**中位姿態附近**，開始錄製瞬間就不會有大收斂段。

## 2 · 錄製（核心指令）

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

要點（其餘參數見 [06](06-record-and-replay.md) 參數表）：

| 項目 | 說明 |
| --- | --- |
| `--dataset.root` | **root 就是資料集目錄本身**，每場換一個新目錄（同名目錄已存在會拒絕啟動） |
| 自動注入的預設值 | 影片編碼 `h264`、編碼執行緒 `2`——`record.py` 啟動時會列印兩行提示；明確傳入 `--dataset.rgb_encoder.vcodec=...` / `--dataset.encoder_threads=...` 可覆寫（原因見 07） |
| 預覽視窗 | 預設開啟（15Hz，`--robot.preview_cameras=false` 可關閉；`--robot.preview_fps` 可調整） |
| `--dataset.video=true` | 雙相機畫面寫入資料集（`observation.images.wrist / top`）；只要腕部相機就移除 `top_camera` |

## 3 · 錄製中的操作

| 按鍵 | 作用 |
| --- | --- |
| `→` 或 `n` | 結束目前回合並儲存 |
| `←` 或 `r` | 捨棄目前回合，原地重錄 |
| `q` | 整場結束，儲存資料集 |

- 回合結束後**方塊自動歸位**，你只需要將主動臂拉回起始姿態；看到 `Recording episode N` 再開始下一回合的動作。
- 儲存階段（數十秒）主控台會列印 `[record.py] reset done; saving the episode + encoding videos now`——
  這段時間**按鍵會被安全忽略**（誤按不會弄壞任何回合），等下一行 `Recording episode` 出現再操作。
- 編碼失敗有**自動重試兜底**（列印 `video encode failed ... retrying once` 後 3 秒自動重試）；已儲存的回合永不遺失。

## 4 · 健檢

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

如何解讀輸出：

- **action span 全為 0（或夾爪為 0）的回合**是空錄/無效錄製，刪除並重錄；
- **每回合開頭 `max |act-obs|` 偏大**是收斂段，正常；中後段應小於 ~10 單位。

## 5 · 看影片

```bash
uv run --frozen python examples/so101_mujoco/export_videos.py \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

產物：

- `examples/so101_mujoco/outputs/videos/<数据集名>/epN_top.mp4`、`epN_wrist.mp4` —— **每回合每相機一段可雙擊播放的影片**；
- `examples/so101_mujoco/outputs/renders/<数据集名>_epN_dual.png` —— 每回合一張拼圖（上排頂視、下排腕部，均勻取樣 6 個影格），供快速目視檢查（`--no-strips` 可跳過）。

資料集中也有原始封裝影片（多回合依序拼接在同一個檔案）：
`outputs/datasets/<数据集名>/videos/observation.images.{top,wrist}/chunk-000/file-000.mp4`。

## 6 · 重播（選用）

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision --dataset.episode=0
```

## 7 · 訓練

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

| 要點 | 說明 |
| --- | --- |
| `--policy.type` | 策略類型，**從 `act` 起步**（與這套資料規模/任務最匹配）；`ls src/lerobot/policies/` 可查看其他選擇（diffusion / smolvla / pi0 等） |
| `--policy.push_to_hub=false` | **必加**——預設會想推送至 HuggingFace Hub，未設定 `repo_id` 會直接報錯結束；要推送時改為 `--policy.repo_id=你的用户名/模型名`（需先 `hf auth login`） |
| `--policy.device=cpu` | 本機無獨立顯示卡使用 `cpu`；有 NVIDIA 顯示卡的機器刪除該參數（自動使用 cuda） |
| 產物 | `output_dir/checkpoints/<步数>/` 與 `checkpoints/last/pretrained_model/`——部署時指向後者；續訓用的 `train_config.json` 也在裡面 |
| 續訓 | 中斷後在原指令加上：`--resume=true --config_path=<output_dir>/checkpoints/last/pretrained_model/train_config.json` |

**本機速度預期**：純 CPU 約 **2 秒/步**（batch 2、480p 雙相機；實測 12 步冒煙 loss 從 70 降到 22，方向正常）。
因此本機適合小步數驗證鏈路——教學自帶的 `outputs/train/smoke_act` 就是 12 步的產物；
**正式訓練（ACT 通常 10 萬步量級）建議改用配備 GPU 的機器，指令完全相同。**

> 相依性提示：訓練需要 `training` extra（accelerate 等）。若顯示 `accelerate is required but not installed`，
> 依 [01](01-environment.md) 的安裝指令補上 `--extra training` 後重試。

## 8 · 部署（讓策略在模擬中自己幹活）

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/rollout.py \
    --policy.path=examples/so101_mujoco/outputs/train/act_so101_sim_vision/checkpoints/last/pretrained_model \
    --strategy.type=base \
    --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --task="put the cube in the box" --duration=30
```

| 要點 | 說明 |
| --- | --- |
| 相機參數 | `--robot.image_camera/--robot.top_camera` **必須與錄製資料集時一致**（sim_cam + top_cam），否則策略拿不到它訓練過的畫面 |
| `--task` | 與錄製時的 `--dataset.single_task` 一致 |
| `--duration` | 執行滿多少秒後自動收場（收場前會將機械臂送回初始位姿再中斷連線）；中途按 `Ctrl-C` 也可停止 |
| 想先試通鏈路 | 使用教學自帶的示範模型即可：`--policy.path=examples/so101_mujoco/outputs/train/smoke_act/checkpoints/last/pretrained_model`（12 步訓練，動作接近亂動，僅驗證鏈路） |
| 純 CPU 部署 | 策略推論偶爾出現 0.5s 尖峰，會提示 `Control loop is running slower ... than the target FPS`——在模擬中能執行但會卡頓；GPU 上沒有此問題（實測 20s 冒煙全程可執行、正常收場） |
| 實機部署 | 將 `--robot.*` 換成實機：`--robot.type=so101_follower --robot.port=COMxx --robot.id=juxi_so101 --robot.use_degrees=false`（注意桌面留出空間） |
| 其他模式 | `--strategy.type=sentry / highlight / dagger / episodic`：邊跑邊錄 / 環形緩衝按鍵儲存 / 人在迴圈中糾正 / 回合制錄製，見 `lerobot-rollout --help` |

## 附錄 A · 改用 conda 環境（選用）

本儲存庫預設使用 **uv 管理的專案內 `.venv`**（見 [01](01-environment.md)），執行指令都要帶
`uv run --frozen --with mujoco` 前綴。如果你更習慣 conda，做法是**將「建立環境」那一步換成以下三條指令**，
之後**所有指令都移除 uv 前綴**（`python examples/...` 直接執行），也不再需要 `UV_CACHE_DIR`
（那是 uv 的跨磁碟快取特例，與 conda 無關）：

```bash
# 一次性：在仓库根目录建好环境（python 版本对齐 01 的 3.12）
conda create -n lerobot-sim python=3.12 -y
conda activate lerobot-sim
pip install -e .            # 安装本仓库 lerobot 及其依赖（含 torch，Windows 上 pip 默认就是 CPU 版）
pip install "mujoco==3.16"  # uv 路线用 --with mujoco 临时提供，conda 路线装成常驻依赖
```

之後例如錄製就變成：

```bash
python examples/so101_mujoco/record.py --robot.image_camera=sim_cam ...
```

兩個注意事項：

1. **版本對齊**：`pip install -e .` 由 pip 自行解析版本，未必和 `uv.lock` 完全一致；
   想要與目前實測環境完全一致的組合，可用 uv 依鎖定檔安裝到 conda 環境中：

   ```bash
   uv pip sync uv.lock --python "$(conda run -n lerobot-sim python -c 'import sys; print(sys.executable)')"
   pip install "mujoco==3.16"
   ```

2. 主動臂的校正快取儲存在 `~/.cache/huggingface/lerobot/calibration/`，與使用哪個環境無關，遷移環境不需重新校正。

## 附錄 B · 常見坑快速查閱

| 現象 | 一句話 |
| --- | --- |
| 序列埠打不開 | 先列出連接埠，編號可能已改變（第 0 步） |
| 儲存時主控台安靜數十秒 | 正在編碼，屬正常；看到 `saving the episode...` 提示就別按鍵 |
| 錄製時畫面偶爾卡頓 | 儲存時段的編碼資源競爭；控制迴路本身不受影響（以 cadence 數字為準），詳見 07 |
| 崩潰一次還能救嗎 | 已儲存的回合永不遺失；`record.py --resume=true ... --dataset.num_episodes=N` 續錄 |
| `lerobot-train` 顯示 `'repo_id' argument missing` | 預設會想推送至 Hub：加上 `--policy.push_to_hub=false`（要推送就設定 `--policy.repo_id` 並先 `hf auth login`） |
| 部署時策略不動或亂動 | 先核對 `--robot.image_camera/--robot.top_camera` 和 `--task` 是否與錄製時一致；再看是否只訓練了很少步數 |

所有坑與解法（含記憶體吃緊、編碼 OOM、空回合等）見 [07 · 常見問題](07-troubleshooting.md)。

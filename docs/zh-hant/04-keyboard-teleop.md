# 04 · 鍵盤遙控操作

用鍵盤「點動」關節來手動控制實機或模擬臂——不需要主動臂時最快的控制方式，也是錄製示範資料的手段之一。

## 指令

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

（`teleoperate.py` 的預設值就是 `--robot.type=so101_mujoco --teleop.type=so101_keyboard`。）

## 按鍵（按住才生效，全域監聽——視窗焦點在哪裡都行）

| 按鍵 | 動作 | 按鍵 | 動作 |
| --- | --- | --- | --- |
| `w` / `s` | shoulder_lift 上 / 下 | `a` / `z` | shoulder_pan 左 / 右 |
| `e` / `d` | elbow_flex 伸 / 屈 | `t` / `g` | wrist_flex + / − |
| `y` / `h` | wrist_roll + / − | `u` / `j` | 夾爪 張開 / 閉合 |

按鍵是**刻意避開錄製控制鍵**（`n/r/q`、方向鍵、`Esc`）所選的，這樣遙控操作和錄製可以同時進行。

## 關鍵參數

| 參數 | 作用 | 建議值 |
| --- | --- | --- |
| `--teleop.rate` | 按住按鍵時的目標速度（單位/秒） | 預設 60 偏慢；實機手感 **150** 比較合適 |
| `--robot.max_relative_target` | 每個控制週期最多讓關節移動多少單位（安全限速） | 實機 **5**（60Hz 遙控操作）/ **10**（30Hz 錄製） |
| `--robot.use_degrees=false` | 使用行程比例制（−100~100）而非角度制 | **實機必加**，否則單位對不上（模擬預設一致） |

## 行為說明

- **遙控操作期間不要打字**：鍵盤監聽是**全域且不攔截按鍵**的——在電腦上任何視窗敲到對應按鍵
  （`w a s z e d t g y h u j`，包括聊天室裡的拼音）都會同時驅動手臂。使用主動臂模式沒有這個問題。
- **連線瞬間手臂會移動**：實機從動臂會先上扭矩（變硬），然後朝「中點姿態」移動（按鍵前的目標）；
  模擬臂則直接朝中位點位姿收斂。請保持手邊留有空間。
- **結束**：在該終端機按 `Ctrl-C`（或按 `Esc`，鍵盤監聽會中斷並乾淨結束）。結束後實機會**失去扭矩而變軟**，
  請用手扶一下——這是正常行為。
- **啟動日誌裡成串的 `clamped to be safe` WARNING** 是限速器在「追趕」時的正常輸出，到位後會自動停止。

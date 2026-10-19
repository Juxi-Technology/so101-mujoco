# 03 · 實機連線與校正

## 辨識序列埠

CH343 晶片的驅動板插上後即會出現一個 COM 埠；**編號會隨插拔/更換 USB 埠而變化**，每次連線前請先確認：

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen python -c "import serial.tools.list_ports as lp; [print(p.device, '|', p.description, '|', p.hwid) for p in lp.comports()]"
```

## 第一步：唯讀初檢（接線/供電/伺服馬達健檢）

**不寫入任何東西**，先將六顆伺服馬達逐一 ping 一遍，再讀取電壓與溫度（扭矩狀態保持原樣）：

```bash
uv run --frozen python examples/so101_mujoco/hardware_check.py --port COM163
```

正常輸出形如：六行關節、溫度 20~30°C、扭矩 0（手臂可自由活動）。**電壓視供電方式而定**：從動臂接外部
電源時約 11V，主動臂僅靠驅動板供電時約 5V——能將六顆伺服馬達全部讀完即代表接線正常。若有缺失/型號不符
會直接報錯。

## 第二步：校正

校正會將「每個關節的行程範圍 + 中位參考」寫入伺服馬達 EEPROM 並儲存到本機檔案；**從動臂和主動臂都要各校正一次**。
兩台臂的校正檔案分開存放，互不影響：

| 裝置 | 指令 | 校正檔案存放位置 |
| --- | --- | --- |
| 從動臂 | `uv run --frozen lerobot-calibrate --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101` | `~/.cache/huggingface/lerobot/calibration/robots/so_follower/juxi_so101.json` |
| 主動臂 | `uv run --frozen lerobot-calibrate --teleop.type=so101_leader --teleop.port=COM163 --teleop.id=juxi_leader` | `.../calibration/teleoperators/so_leader/juxi_leader.json` |

`id` 可以任意命名，但**之後遙控操作/錄製必須使用同一個 id**，否則會再次提示校正。

### 實體步驟（終端機會列印示意圖）

1. **擺到中位姿態再按 Enter**：底座平放於桌面邊緣，大臂豎直向上、小臂水平朝前，肩部旋轉與腕部居中
   （主動臂的「夾爪」是握把/扳機）。這一刻的位置會被記錄為該臂的「中位參考」。
2. 按 Enter 後**逐一將關節緩慢劃過整個活動範圍**（`wrist_roll` 不需掃掠，會自動按整圈處理），再按 Enter 儲存。

注意事項：

- 從動臂校正期間扭矩為 0（手臂是軟的），請用手扶著移動；主動臂本來就無扭矩。
- 校正過程會向伺服馬達寫入 EEPROM（這是校正的一部分，屬正常）。
- 本次實測校正結果（供對照）：從動臂各關節行程 1474~2688 計數、`wrist_roll` 4095；
  主動臂 2208~2681 計數。行程明顯不對稱是正常的（見 [05 零點微調](05-leader-digital-twin.md) 為何需要進行）。

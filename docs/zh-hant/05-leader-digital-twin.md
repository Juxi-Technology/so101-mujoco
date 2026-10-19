# 05 · 主動臂數位孿生（實體臂驅動模擬臂）

用手拖動**實體主動臂**，讓 **MuJoCo 視窗裡的模擬從動臂**即時鏡像跟隨——數位孿生示範、
模擬資料採集的正確開啟方式。

## 前置條件

主動臂已完成校正（見 [03](03-hardware-calibration.md)），序列埠以 `COM163` 為例。

## 指令

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_mujoco \
    --teleop.type=so101_leader_trim --teleop.port=COM163 --teleop.id=juxi_leader \
    --teleop.use_degrees=false
```

- `--robot.type=so101_mujoco`：受控對象是模擬臂，視窗會自動開啟；
- `--teleop.*`：操控裝置是實體主動臂（純讀取，永不施加扭矩，對主動臂零風險）；
- `--teleop.use_degrees=false`：**必加**。讓主動臂輸出的單位（行程比例制）與模擬臂一致。

將 `--robot.type` 換成 `so101_follower --robot.port=COM172 --robot.id=juxi_so101 --robot.max_relative_target=5`
就是「實體主動臂 → 實機從動臂」的標準套件玩法，同一份主動臂校正通用。

## 零點偏移怎麼辦：自動中心微調（`so101_leader_trim`）

**現象**：主動臂擺到「目視中位」，模擬臂卻偏了幾度。

**原理**：lerobot 的正規化零點 = **校正時掃掠記錄範圍的中點** `(min+max)/2`；而校正按 Enter 時的
「中位姿態」會被記為原始值 2048。只要某個關節的機械行程本身不對稱，兩個「中點」就永遠相差一個固定量
（實測 1 號伺服馬達：記錄範圍 776~3457，中點 2116，與 2048 相差 68 計數 ≈ **5.6°**）。
**這個偏差無法靠重新校正消除**（行程不對稱是機械結構決定的），必須在軟體中補償。

**解法**：`so101_leader_trim` 外掛會從校正檔案中依公式自動算出每個關節的補償並即時扣除，
重新校正後會自動跟隨、無需手動調參：

```
补偿ᵢ = (2048 − minᵢ) / (maxᵢ − minᵢ) × 200 − 100
```

本機實測生效值（啟動日誌會列印）：

| 關節 | 補償（單位） |
| --- | --- |
| shoulder_pan | −5.11 |
| shoulder_lift | −0.92 |
| elbow_flex | +2.54 |
| wrist_flex | +0.69 |

其餘關節偏差 <0.05，無需補償；夾爪（0~100）與角度制模式不參與微調。

> 開發者註記：此外掛的 `name` 必須保持為 `"so_leader"`——`name` 是校正檔案的搜尋目錄鍵，
> 自訂類型名稱會導致找不到校正檔案而誤觸發重新校正流程。

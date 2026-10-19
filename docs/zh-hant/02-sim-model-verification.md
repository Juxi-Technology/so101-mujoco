# 02 · 模擬模型驗證（MJCF 載入與驅動）

## 模型來源

SO-ARM101 的三份公開 MJCF 模型，本專案全部驗證可用：

| 簡稱 | 檔案 | 來源 |
| --- | --- | --- |
| 官方-新校正 | `SO101/so101_new_calib.xml` | TheRobotStudio/SO-ARM100 官方儲存庫；**本儲存庫教學 zip 內有相同副本**（位元組完全一致） |
| 官方-舊校正 | `SO101/so101_old_calib.xml` | 同儲存庫（zip 中沒有，需下載） |
| ROS2 描述套件 | `so_arm101_description/mjcf/so_arm101.xml` | 本儲存庫教學附件 `SO-ARM101_ROS2.zip` |

註：zip 解壓流程由早期版 `so101_assets.py` 提供並保留可供查閱；2026-10-16 起模擬機器人已遷移至
**mujoco_menagerie 的 SO-ARM100 模型**（vendored 於 `assets/menagerie_so_arm100/`，
遷移原因與要點見 [07](07-troubleshooting.md) 設計說明）。

## 驅動與渲染驗證

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen --with mujoco python examples/so101_mujoco/load_and_drive.py \
    --model "<模型路径>" --out-dir out
```

指令碼會輸出結構摘要（關節/致動器/增益/範圍）、渲染一段「六關節逐一掃掠 + 協調正弦」的驗證影片與靜態影格。
結構摘要範例見 `reports/`（隨儲存庫提供）；對照影片（`media/`）檔案較大，不隨儲存庫散布——依上面的指令可隨時重新產生。

## 三模型關鍵差異（實測）

| 項目 | 官方-新校正 | 官方-舊校正 | ROS2 描述套件 |
| --- | --- | --- | --- |
| 零位語意 | 關節**行程中點** | 水平**完全伸展**位置 | 行程中點 |
| 關節名稱 | `shoulder_pan` | 同上 | `shoulder_pan_joint`（後綴） |
| 位置增益 | kp=998.22, kv=2.731 | **kp=17.8, kv=0** | kp=998.22 |
| 夾爪單位 | 弧度 hinge | 弧度 hinge | **0~1 正規化** |
| 自碰撞排除 | 無 | 無 | 有（6 對） |

**跟隨誤差實測**：新校正與描述套件靜止保持誤差 0.0005 rad，舊校正 0.03 rad（下垂約 1.7°，kp 弱 56 倍）。
在模擬中評估同一策略，更換模型會得到不同動態，請注意記錄使用的是哪一份。

## 必須記住的模型行為

1. **`shoulder_lift` 正方向朝下**：驅動力矩中「下擺」使用正角度，進行遙控操作映射或資料換算時請先驗證符號。
2. **壓地即擋**：下擺極限會讓指尖接觸地面並被擋停（指令碼內建 8cm 離地保護會自動裁減幅度）。
3. 官方模型無相機、無 keyframe；帶相機的變體 `so101_new_calib_camera.xml` 存在，後續錄製視覺資料時可使用。

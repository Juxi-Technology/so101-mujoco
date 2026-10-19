# 06 · 데이터 녹화와 리플레이

## 녹화 명령 템플릿

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

## 파라미터 요점(놓치기 쉬운 것)

| 파라미터 | 설명 |
| --- | --- |
| `--dataset.root` | **root가 곧 데이터셋 디렉터리 자체**입니다(상위 디렉터리 + repo_id 조합이 아님). 녹화할 때마다 새 디렉터리로 변경하세요 |
| `--dataset.repo_id` | 로컬 녹화에서는 식별자일 뿐이며, 나중에 Hub에 푸시할 때만 실제 `用户名/名字`가 필요합니다 |
| `--dataset.no_stamp=true` | 타임스탬프 접미사를 붙이지 않아 디렉터리/이름이 안정적입니다. 같은 이름으로 다시 녹화하려면 기존 디렉터리를 먼저 삭제해야 합니다 |
| `--dataset.episode_time_s` | 에피소드당 **상한**(보험용). 정상 조작에서는 `→`를 눌러 미리 종료합니다 |
| `--dataset.reset_time_s` | 에피소드 사이에 기록하지 않는 정리 시간. 이 시간에도 리더 암은 계속 실시간으로 팔로워 암을 구동합니다. **시뮬레이션 녹화에서는 이 단계에 들어가면 블록이 자동으로 초기 위치로 순간이동합니다**(아래 참조) |
| `--dataset.video` | 카메라 데이터가 필요할 때만 켭니다(비전 데이터셋은 반드시 true; pyav 폴백은 검증 완료) |
| `--dataset.rgb_encoder.vcodec` | 비디오 인코더. **이 머신의 듀얼 카메라 녹화에는 `h264` 사용**: `record.py`가 기본으로 주입합니다(업스트림 기본값 libsvtav1은 두 인코딩을 동시에 열 때 메모리 할당 실패로 세션 전체가 크래시 — [07](07-troubleshooting.md) 참조). 명시적으로 전달하면 주입하지 않습니다 |
| `--dataset.encoder_threads` | 인코딩 스레드 수. **`record.py`가 기본으로 2를 주입**: 기본값은 모든 코어를 사용해 저장 중 시뮬레이션 화면이 눈에 띄게 끊깁니다([07](07-troubleshooting.md) 참조). 인코딩당 2스레드로 제한하면 저장 시에도 시뮬레이션이 부드럽게 유지됩니다. 명시적으로 전달하면 주입하지 않습니다 |
| `--dataset.push_to_hub` | 이 머신에서 HF에 직접 연결하려면 프록시가 필요하므로 일단 false로 두고, 녹화 후 수동으로 푸시합니다 |

## 에피소드 제어 키(전역, 녹화 중 항상 유효)

| 키 | 역할 |
| --- | --- |
| `→` 또는 `n` | 현재 에피소드 종료(**저장**) |
| `←` 또는 `r` | 현재 에피소드를 버리고 **같은 자리에서 재녹화**(에피소드 하나가 마음에 들지 않을 때 사용, 세션을 재시작할 필요 없음) |
| `q` | 세션 전체 종료, 데이터셋 저장(**권장**) |
| `Esc` | `q`와 동일(키보드 텔레오퍼레이션도 함께 끊김; 깔끔한 종료는 검증되었지만 `q` 사용을 우선 권장) |

**조작 권장 사항**: 녹화 시작 전에 리더 암을 중간 자세 근처에 두세요(녹화 시작 순간 시뮬레이션/실기 암이 "휙 이동"하는 수렴 구간이 녹화되는 것을 방지).
녹화 시작 후 1초 정도 정지한 뒤 동작을 시작하세요.

## 시뮬레이션 녹화의 자동 장면 리셋

실기 녹화에서는 "Reset the environment" 단계에서 블록을 직접 제자리에 돌려놓아야 합니다. 시뮬레이션에서는 녹화 런처(`record.py`)가
해당 단계가 시작될 때 **세 개의 블록을 자동으로 초기 위치로 순간이동**시키므로(속도도 0으로 초기화), 각 에피소드에서 `→`로 종료한 뒤
리더 암만 시작 자세로 되돌리면 블록은 자동으로 제자리를 찾아가고, 다음 에피소드는 고정된 초기 장면에서 시작됩니다.
실기 팔로워 암에는 이 동작이 없으며(평소처럼 직접 배치), `teleoperate.py`/`replay.py`도 관련이 없습니다.

## 녹화 후 점검

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

각 에피소드의 프레임 수, 길이, 6개 관절 동작 폭과 추종 오차를 출력합니다:

- **action span = 0인 에피소드**는 빈 녹화(사람이 움직이지 않음)이므로 삭제하고 다시 녹화하면 됩니다.
- **시작 부분의 |action−obs|가 큰 것**은 수렴 구간(정상)이며, 중후반은 일반적으로 <10 단위입니다.

## 시뮬레이션에서 "화면 포함" 데이터 녹화(손목 카메라)

시뮬레이션 로봇은 장면의 손목 카메라(`sim_cam`)를 이미지 관측으로 데이터셋에 녹화하는 것을 지원합니다:

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

요점: `--robot.image_camera=sim_cam`(카메라 이름) + `--dataset.video=true`(이미지는 비디오 인코딩 사용, pyav 폴백 검증 완료).
데이터셋 피처에 `observation.images.wrist`(480×640×3)가 나타납니다. 해상도와 프레임레이트는
`--robot.image_width/--robot.image_height/--robot.image_fps`로 조정할 수 있습니다.
창을 열 때(`onscreen=true`, 기본값)는 메인 뷰 창 외에 **카메라마다 실시간 미리보기 창이 하나씩** 열립니다
(손목 / 탑뷰, 창 왼쪽 위에 라벨 표시). 녹화 중에 두 화면이 정상인지 바로 확인할 수 있으며, 필요 없으면
`--robot.preview_cameras=false`를 추가합니다. 미리보기 창은 기본적으로 **15Hz**로 갱신되며(`--robot.preview_fps`로 조정 가능),
상태 표시용이므로 메인 창의 50Hz를 따라갈 필요가 없어 같은 화면에 창 3개를 띄울 때 렌더링 부담이 훨씬 적습니다.

**장면과 탑뷰 카메라(2026-10-16부터)**: 시뮬레이션 장면에는 작업 영역이 기본 포함되어 있습니다. 받침판, 삼색 블록(34mm), 수납함(`so101_assets.add_workspace` 참조,
레이아웃은 `preview_workspace.py`로 렌더링하며 미세 조정 가능)이 있으며, 별도로 고정 탑뷰 카메라 `top_cam`이 있습니다(화면 위쪽 = 로봇 팔에서 멀어지는 방향).
`--robot.top_camera=top_cam`을 추가하면 탑뷰 화면을 `observation.images.top`으로 녹화합니다(듀얼 카메라 동시 녹화). 손목 카메라만 원하면 이 파라미터를 제거하세요.
에피소드 종료 후 비디오 인코딩은 두 화면을 동시에 처리하므로 대기 시간이 조금 긴 것은 정상입니다.

## 리플레이

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

> 공식 `lerobot-replay` 진입점은 이 프로젝트의 플러그인을 로드하지 않으므로, 직접 사용하면 `invalid choice: 'so101_mujoco'` 오류가 발생합니다.
> 따라서 통일해서 `replay.py` 런처를 사용합니다.

## 데이터셋 형식과 위치

데이터셋은 LeRobotDataset v3입니다. `action`과 `observation.state`는 모두 6차원 벡터
(`shoulder_pan.pos … gripper.pos`)이며, 공식 실기 데이터셋과 동일하여 바로 혼합 학습할 수 있습니다.

```
examples/so101_mujoco/outputs/datasets/
└── juxi_teleop_run1/   真机键盘遥操（1 回合 / 2430 帧 / 81s）✅ 保留的真机数据

> 2026-10-16 清理：旧的仿真录制（`sim_run2`、`sim_vision_demo`、`sim_vision_run1/2/3`）
> 已全部删除。**正式数据集 `so101_sim_vision`（双相机 / 5 回合 / 10610 帧 / 353.8s / h264）
> 已于当晚录成 ✅**；每回合单机视频导出在 `outputs/videos/so101_sim_vision/`，
> 双相机预览拼图在 `outputs/renders/sim_vision_epN_dual.png`。
```

## 이번 실측 기록(2026-10-15)

| 세션 | 내용 | 결과 |
| --- | --- | --- |
| 실기 run1 | 키보드 텔레오퍼레이션으로 실기 녹화 | 1 에피소드 81s, 6개 관절 폭 75~140 단위, 30Hz 안정 |
| 실기 리플레이 | 동일 에피소드 재생 | 2430 프레임 완전 재현, 이상 없음 |
| 시뮬레이션 run2 | 리더 암 텔레오퍼레이션으로 시뮬레이션 녹화 | 5 에피소드 157s, ep1~4 추종 오차 <12 단위 |
| 시뮬레이션 리플레이 ep1 | 창에서 재연 | 궤적이 조작과 일치(확인 완료) |

## 추가 실측(2026-10-16)

| 세션 | 내용 | 결과 |
| --- | --- | --- |
| 새 리더 암(COM124) | 재캘리브레이션(새 암/새 서보) | ✅ 캘리브레이션 성공; `so101_leader_trim` 영점 보정이 새 캘리브레이션에 자동 적응 |
| 비전 run1 | 리더 암 텔레오퍼레이션으로 시뮬레이션 녹화(화면 포함) | 2 에피소드 / 3177 프레임 / 106s @ 29.97Hz; 추종 오차 전 구간 ≤2 단위(첫 프레임 수렴 0.5s만 해당); `observation.images.wrist` 비디오 저장 및 디코딩 검증 ✅ |
| 비전 run2 | 듀얼 카메라 이어서 녹화(`--resume`) | ep0(2776 프레임 / 92.6s) 무손실; ep1 저장 시 libsvtav1 인코더 OOM으로 세션 전체 크래시 → 인코더를 h264로 변경(`record.py` 기본 주입)하고 엔드투엔드 실측 통과(2 에피소드 × 2경로 인코딩); 잔여물 정리 완료, 정식 재녹화는 run3로 이전 |
| 비전 run3 | 듀얼 카메라 정식 녹화(h264) | 1차 세션: ep0(185.2s / 5554 프레임) + ep1(72.8s / 2186 프레임) 저장 완료 및 점검 통과; 세션 간 인코딩 정지 중 `→`를 연타해 빈 에피소드 크래시 발생(메커니즘과 보호 조치는 [07](07-troubleshooting.md) 참조) → 이어서 나머지 에피소드 녹화(5 에피소드 계획) |
| 정식 녹화 첫 시도(so101_sim_vision) | 듀얼 카메라(h264 + 2스레드 + 미리보기 창 15Hz) | ep0(82.3s / 2469 프레임) 저장 시 인코더 메모리 할당 실패로 세션 전체 크래시(시스템 commit 거의 포화, [07](07-troubleshooting.md) 참조) → **인코딩 실패 자동 재시도**와 **콘솔 음소거** 추가(모두 실측 적용 확인, 스모크 26개 항목 전부 통과); 머신 재부팅 후 정식 재녹화 예정 |
| 정식 녹화(so101_sim_vision) ✅ | 듀얼 카메라 리더 암 텔레오퍼레이션, 5 에피소드 | **5/5 에피소드 전부 저장**: 61.5 / 53.4 / 101.1 / 62.4 / 75.4 s, 총 10610 프레임 @29.97Hz, tick 예산 초과 0건, 크래시 없음; 6축+그리퍼 전 구간 유효 동작; 2경로 비디오 디코딩 검증 통과 |

# 09 · 전체 사용 튜토리얼(암 준비 → 데이터셋 → 영상 확인 → 학습 → 배포)

> 원스톱 조작 매뉴얼: 그대로 따라 하면 "리더 암 연결"부터 "학습된 정책이 시뮬레이션에서 스스로 작업"까지 한 번에 진행할 수 있습니다.
> 전제: 환경은 [01](01-environment.md)에 따라 설치되었고, 리더 암은 [03](03-hardware-calibration.md)에 따라 캘리브레이션되었습니다
> (이 머신은 `juxi_leader` / COM124). 녹화 관련 문제는 모두 [07](07-troubleshooting.md)에 모여 있습니다.

## 0 · 일회성 준비

```bash
# 本机所有 uv 命令都要先设（跨盘缓存特例，见 07）
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
```

리더 암을 연결하고 시리얼 포트를 확인합니다(**분리/재연결할 때마다 번호가 바뀔 수 있음**):

```bash
uv run --frozen python -c "from serial.tools import list_ports; print([p.device for p in list_ports.comports()])"
```

책상에 공간을 확보하세요. 녹화 시 **3개의 창**이 팝업됩니다(메인 뷰 + `wrist camera - live` + `top camera - live`).

## 1 · 텔레오퍼레이션 워밍업(권장)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_mujoco \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader \
    --teleop.use_degrees=false
```

리더 암을 움직여 시뮬레이션 암이 잘 따라오는지 확인하세요. 종료(Ctrl-C) 전에 리더 암을 **중간 자세 근처**에 멈춰 두면, 녹화 시작 순간 큰 수렴 구간이 생기지 않습니다.

## 2 · 녹화(핵심 명령)

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

요점(나머지 파라미터는 [06](06-record-and-replay.md) 파라미터 표 참조):

| 항목 | 설명 |
| --- | --- |
| `--dataset.root` | **root가 곧 데이터셋 디렉터리 자체**입니다. 세션마다 새 디렉터리로 변경하세요(같은 이름의 디렉터리가 있으면 시작을 거부함) |
| 자동 주입 기본값 | 비디오 인코딩 `h264`, 인코딩 스레드 `2` — `record.py`가 시작 시 두 줄의 안내를 출력합니다. `--dataset.rgb_encoder.vcodec=...` / `--dataset.encoder_threads=...`를 명시하면 덮어쓸 수 있습니다(이유는 07 참조) |
| 미리보기 창 | 기본 켜짐(15Hz, `--robot.preview_cameras=false`로 끄기, `--robot.preview_fps`로 조정) |
| `--dataset.video=true` | 듀얼 카메라 화면 저장(`observation.images.wrist / top`). 손목 카메라만 원하면 `top_camera`를 제거하세요 |

## 3 · 녹화 중 조작

| 키 | 역할 |
| --- | --- |
| `→` 또는 `n` | 현재 에피소드 종료 및 저장 |
| `←` 또는 `r` | 현재 에피소드 폐기, 같은 자리에서 재녹화 |
| `q` | 세션 전체 종료, 데이터셋 저장 |

- 에피소드 종료 후 **블록이 자동으로 제자리로 돌아가므로**, 리더 암만 시작 자세로 되돌리면 됩니다. `Recording episode N`이 보이면 다음 에피소드 동작을 시작하세요.
- 저장 단계(수십 초)에는 콘솔에 `[record.py] reset done; saving the episode + encoding videos now`가 출력됩니다.
  이 시간 동안 **키 입력은 안전하게 무시**되므로(실수로 눌러도 어떤 에피소드도 손상되지 않음), 다음 줄 `Recording episode`가 나타난 뒤 조작하세요.
- 인코딩 실패에는 **자동 재시도 안전장치**가 있습니다(`video encode failed ... retrying once` 출력 후 3초 뒤 자동 재시도); 이미 저장된 에피소드는 절대 유실되지 않습니다.

## 4 · 점검

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

출력 읽는 방법:

- **action span이 전부 0(또는 그리퍼가 0)인 에피소드**는 빈 녹화/무효 녹화이므로 삭제하고 다시 녹화하세요.
- **각 에피소드 시작의 `max |act-obs|`가 큰 것**은 수렴 구간으로 정상입니다. 중후반은 ~10 단위 미만이어야 합니다.

## 5 · 영상 확인

```bash
uv run --frozen python examples/so101_mujoco/export_videos.py \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

산출물:

- `examples/so101_mujoco/outputs/videos/<数据集名>/epN_top.mp4`, `epN_wrist.mp4` — **에피소드마다 카메라마다 하나씩, 더블클릭으로 재생 가능한 비디오**;
- `examples/so101_mujoco/outputs/renders/<数据集名>_epN_dual.png` — 에피소드마다 한 장의 몽타주(윗줄 탑뷰, 아랫줄 손목, 균등 샘플링 6프레임), 빠른 육안 점검용(`--no-strips`로 생략 가능).

데이터셋 안에도 원본 패키징 비디오가 있습니다(여러 에피소드가 순서대로 한 파일에 이어짐):
`outputs/datasets/<数据集名>/videos/observation.images.{top,wrist}/chunk-000/file-000.mp4`.

## 6 · 리플레이(선택)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision --dataset.episode=0
```

## 7 · 학습

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

| 요점 | 설명 |
| --- | --- |
| `--policy.type` | 정책 유형. **`act`로 시작**(이 데이터 규모/작업에 가장 적합). `ls src/lerobot/policies/`로 다른 선택지(diffusion / smolvla / pi0 등) 확인 가능 |
| `--policy.push_to_hub=false` | **필수** — 기본적으로 HuggingFace Hub에 푸시하려 하며, `repo_id`가 없으면 바로 오류로 종료됩니다. 푸시하려면 `--policy.repo_id=你的用户名/模型名`로 바꾸세요(먼저 `hf auth login` 필요) |
| `--policy.device=cpu` | 이 머신은 외장 GPU가 없어 `cpu` 사용; NVIDIA GPU가 있는 머신은 이 파라미터를 삭제하세요(자동으로 cuda 사용) |
| 산출물 | `output_dir/checkpoints/<步数>/`와 `checkpoints/last/pretrained_model/` — 배포는 후자를 가리킴; 이어서 학습할 때 쓰는 `train_config.json`도 그 안에 있음 |
| 이어서 학습 | 중단 후 기존 명령에 추가: `--resume=true --config_path=<output_dir>/checkpoints/last/pretrained_model/train_config.json` |

**이 머신의 속도 예상**: 순수 CPU에서 약 **2초/스텝**(batch 2, 480p 듀얼 카메라; 실측 12스텝 스모크에서 loss가 70에서 22로 감소, 방향 정상).
따라서 이 머신은 소량 스텝으로 파이프라인을 검증하는 데 적합합니다. 튜토리얼에 포함된 `outputs/train/smoke_act`가 바로 12스텝의 산출물입니다.
**정식 학습(ACT 기준 보통 10만 스텝 규모)은 GPU가 있는 머신으로 바꾸는 것을 권장하며, 명령은 완전히 동일합니다.**

> 의존성 안내: 학습에는 `training` extra(accelerate 등)가 필요합니다. `accelerate is required but not installed` 오류가 나면
> [01](01-environment.md)의 설치 명령에 `--extra training`을 추가한 뒤 다시 시도하세요.

## 8 · 배포(정책이 시뮬레이션에서 스스로 작업하게 하기)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/rollout.py \
    --policy.path=examples/so101_mujoco/outputs/train/act_so101_sim_vision/checkpoints/last/pretrained_model \
    --strategy.type=base \
    --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --task="put the cube in the box" --duration=30
```

| 요점 | 설명 |
| --- | --- |
| 카메라 파라미터 | `--robot.image_camera/--robot.top_camera`는 **데이터셋 녹화 시와 반드시 일치**해야 합니다(sim_cam + top_cam). 그렇지 않으면 정책이 학습했던 화면을 받지 못합니다 |
| `--task` | 녹화 시의 `--dataset.single_task`와 일치해야 합니다 |
| `--duration` | 설정한 초만큼 실행 후 자동 종료(종료 전 로봇 암을 초기 자세로 복귀시킨 후 연결 해제); 중간에 `Ctrl-C`로도 중지 가능 |
| 파이프라인부터 시험하고 싶다면 | 튜토리얼 내장 데모 모델을 사용하면 됩니다: `--policy.path=examples/so101_mujoco/outputs/train/smoke_act/checkpoints/last/pretrained_model`(12스텝 학습, 동작은 거의 무작위에 가까우므로 파이프라인만 검증) |
| 순수 CPU 배포 | 정책 추론에서 간헐적으로 0.5s 스파이크가 발생해 `Control loop is running slower ... than the target FPS`가 표시됩니다. 시뮬레이션에서 실행은 되지만 끊깁니다. GPU에서는 이 문제가 없습니다(실측 20s 스모크 전 구간 실행 및 정상 종료) |
| 실기 배포 | `--robot.*`를 실기로 교체: `--robot.type=so101_follower --robot.port=COMxx --robot.id=juxi_so101 --robot.use_degrees=false`(책상 공간 확보 주의) |
| 기타 모드 | `--strategy.type=sentry / highlight / dagger / episodic`: 실행하며 녹화 / 링 버퍼 + 키로 저장 / 인간 개입 교정(human-in-the-loop) / 에피소드 단위 녹화. `lerobot-rollout --help` 참조 |

## 부록 A · conda 환경으로 전환(선택)

이 저장소는 기본적으로 **uv가 관리하는 프로젝트 내 `.venv`**를 사용하며([01](01-environment.md) 참조), 실행 명령에
`uv run --frozen --with mujoco` 접두사를 붙여야 합니다. conda가 더 익숙하다면, **"환경 만들기" 단계를 아래 세 명령으로 바꾸고**,
이후 **모든 명령에서 uv 접두사를 제거하면**(`python examples/...`로 바로 실행) 됩니다. `UV_CACHE_DIR`도 더 이상 필요 없습니다
(그것은 uv의 크로스 드라이브 캐시 특례일 뿐 conda와는 무관):

```bash
# 一次性：在仓库根目录建好环境（python 版本对齐 01 的 3.12）
conda create -n lerobot-sim python=3.12 -y
conda activate lerobot-sim
pip install -e .            # 安装本仓库 lerobot 及其依赖（含 torch，Windows 上 pip 默认就是 CPU 版）
pip install "mujoco==3.16"  # uv 路线用 --with mujoco 临时提供，conda 路线装成常驻依赖
```

이후에는 예를 들어 녹화가 다음과 같이 됩니다:

```bash
python examples/so101_mujoco/record.py --robot.image_camera=sim_cam ...
```

두 가지 주의점:

1. **버전 정렬**: `pip install -e .`는 pip이 버전을 자체 해석하므로 `uv.lock`과 완전히 일치하지 않을 수 있습니다.
   현재 실측 환경과 한 글자도 다르지 않은 조합을 원한다면, uv로 conda 환경에 잠금 파일대로 설치하세요:

   ```bash
   uv pip sync uv.lock --python "$(conda run -n lerobot-sim python -c 'import sys; print(sys.executable)')"
   pip install "mujoco==3.16"
   ```

2. 리더 암의 캘리브레이션 캐시는 `~/.cache/huggingface/lerobot/calibration/`에 저장되며, 어떤 환경을 쓰든 무관하므로 환경을 옮겨도 다시 캘리브레이션할 필요가 없습니다.

## 부록 B · 흔한 문제 빠른 참조

| 증상 | 한 줄 요약 |
| --- | --- |
| 시리얼 포트가 열리지 않음 | 먼저 포트를 나열하세요. 번호가 바뀌었을 수 있습니다(0단계) |
| 저장 시 콘솔이 수십 초 조용함 | 인코딩 중이며 정상입니다. `saving the episode...` 안내가 보이면 키를 누르지 마세요 |
| 녹화 중 화면이 간헐적으로 끊김 | 저장 구간의 인코딩 리소스 경쟁입니다. 제어 루프 자체는 영향받지 않습니다(cadence 수치 기준). 자세한 내용은 07 참조 |
| 한 번 크래시 나도 복구 가능한가 | 저장된 에피소드는 절대 유실되지 않습니다. `record.py --resume=true ... --dataset.num_episodes=N`으로 이어서 녹화하세요 |
| `lerobot-train`이 `'repo_id' argument missing` 보고 | 기본적으로 Hub 푸시를 시도합니다. `--policy.push_to_hub=false`를 추가하세요(푸시하려면 `--policy.repo_id` 설정 후 먼저 `hf auth login`) |
| 배포 시 정책이 움직이지 않거나 이상하게 움직임 | 먼저 `--robot.image_camera/--robot.top_camera`와 `--task`가 녹화 시와 일치하는지 확인하고, 학습 스텝이 너무 적지 않은지 확인하세요 |

모든 문제와 해결법(메모리 부족, 인코딩 OOM, 빈 에피소드 등)은 [07 · 자주 발생하는 문제](07-troubleshooting.md)를 참조하세요.

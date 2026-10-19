# 01 · 환경 준비

일회성 작업입니다. 이 저장소는 **프로젝트 내부에 격리된 `.venv`를 uv로 관리**합니다. `uv run`은 이 디렉터리의 환경만 사용하며
당신의 conda는 건드리지 않습니다(의도된 설계입니다. [07 자주 발생하는 문제](07-troubleshooting.md) 참조).

## 설치

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'   # 本机特例，见 07

# CPU 版 torch（本机无独显；有 NVIDIA GPU 的机器去掉 UV_TORCH_BACKEND 并参考 pyproject 注释换 CUDA 版）
UV_TORCH_BACKEND=cpu uv sync --frozen --extra core_scripts --extra feetech --extra pynput-dep --extra training
```

네 가지 extra의 용도:

| extra | 제공하는 것 | 필요한 경우 |
| --- | --- | --- |
| `core_scripts` | 공식 record / teleoperate / calibrate / replay 진입점 + 데이터셋 + 시각화 의존성 | 전체 |
| `feetech` | `scservo_sdk`(STS3215 서보 시리얼 프로토콜) | 실기 관련 작업 |
| `pynput-dep` | 전역 키보드 리스닝 | 키보드 텔레오퍼레이션, 녹화 에피소드 제어 키 |
| `training` | `accelerate` / `wandb` 등 | `lerobot-train` 학습, 정책 배포(`lerobot-rollout`) |

필요할 때 MuJoCo를 임시로 추가합니다(잠금 파일에 포함되지 않고 필요 시 로드):

```bash
uv run --frozen --with mujoco python <脚本>
```

**conda 환경을 쓰고 싶으신가요?** 그러면 실행 명령에 `uv run` 접두사가 필요 없습니다. 환경을 만드는 세 가지 명령과 주의점은
[09 전체 사용 튜토리얼 · 부록 A](09-usage-tutorial.md)를 참조하세요.

## 검증

```bash
uv run --frozen --with mujoco python -c "import mujoco, scservo_sdk, pynput, lerobot, torch; print('OK')"
uv run --frozen lerobot-calibrate --help | head -3   # 官方入口可用
```

## 자주 발생하는 문제

- **`uv sync`가 `failed to persist temporary file ... os error 17`을 보고하는 경우**: 이 머신의 uv 캐시 디렉터리 크로스 드라이브
  특례입니다. 위의 `UV_CACHE_DIR` 접두사를 사용하면 되며, 자세한 내용은 [07](07-troubleshooting.md)을 참조하세요.
- **Microsoft Store 버전 Python을 사용하지 마세요**: uv가 자동 관리하는 Python 3.12를 선택하면 됩니다.
- 최초 `uv run --with mujoco` 실행 시 약 5.6MB의 mujoco wheel을 다운로드하며, 이후에는 캐시를 사용합니다.

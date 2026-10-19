# 03 · 실기 연결과 캘리브레이션

## 시리얼 포트 식별

CH343 칩 드라이버 보드는 연결하면 COM 포트가 나타납니다. **번호는 분리/재연결이나 USB 포트 변경에 따라 바뀌므로**, 연결할 때마다 먼저 확인하세요:

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen python -c "import serial.tools.list_ports as lp; [print(p.device, '|', p.description, '|', p.hwid) for p in lp.comports()]"
```

## 첫 번째 단계: 읽기 전용 초기 점검(배선/전원/서보 점검)

**아무것도 쓰지 않고**, 먼저 6개 서보를 하나씩 ping한 뒤 전압과 온도를 읽습니다(토크 상태는 그대로 유지):

```bash
uv run --frozen python examples/so101_mujoco/hardware_check.py --port COM163
```

정상 출력은 대략 6줄의 관절, 온도 20~30°C, 토크 0(암이 자유로운 상태)입니다. **전압은 전원 공급 방식에 따라 다릅니다**: 팔로워 암에 외부
전원을 연결하면 약 11V, 리더 암이 드라이버 보드 전원만 사용하면 약 5V이며, 6개 서보를 모두 읽을 수 있으면 배선이 정상입니다. 누락/모델 불일치가
있으면 바로 오류가 발생합니다.

## 두 번째 단계: 캘리브레이션

캘리브레이션은 "각 관절의 스트로크 범위 + 중간 위치 기준"을 서보 EEPROM에 기록하고 로컬 파일로 저장합니다. **팔로워 암과 리더 암을 각각 한 번씩 캘리브레이션해야 합니다**.
두 암의 캘리브레이션 파일은 별도로 저장되어 서로 영향을 주지 않습니다:

| 장치 | 명령 | 캘리브레이션 파일 위치 |
| --- | --- | --- |
| 팔로워 암 | `uv run --frozen lerobot-calibrate --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101` | `~/.cache/huggingface/lerobot/calibration/robots/so_follower/juxi_so101.json` |
| 리더 암 | `uv run --frozen lerobot-calibrate --teleop.type=so101_leader --teleop.port=COM163 --teleop.id=juxi_leader` | `.../calibration/teleoperators/so_leader/juxi_leader.json` |

`id`는 임의로 지정할 수 있지만, **이후 텔레오퍼레이션/녹화에서 반드시 같은 id를 사용해야 합니다**. 그렇지 않으면 다시 캘리브레이션하라는 메시지가 나옵니다.

### 물리적 절차(터미널에 그림이 출력됨)

1. **중간 자세로 놓고 Enter**: 베이스를 책상 가장자리에 평평하게 놓고, 큰 팔은 수직 위로, 작은 팔은 수평 앞으로, 어깨 회전과 손목은 중앙에 맞춥니다
   (리더 암의 "그리퍼"는 핸들/트리거입니다). 이 순간의 위치가 해당 암의 "중간 위치 기준"으로 기록됩니다.
2. Enter 후 **각 관절을 하나씩 천천히 전체 가동 범위로 움직입니다**(`wrist_roll`은 스윕할 필요 없이 자동으로 전체 회전으로 처리됨). 그다음 Enter로 저장합니다.

주의 사항:

- 팔로워 암은 캘리브레이션 동안 토크가 0이므로(암이 힘없이 늘어짐) 손으로 잡고 움직입니다. 리더 암은 원래 토크가 없습니다.
- 캘리브레이션 과정에서 서보 EEPROM에 기록합니다(캘리브레이션의 일부이므로 정상입니다).
- 이번 실측 캘리브레이션 결과(참고용): 팔로워 암 각 관절 스트로크 1474~2688 카운트, `wrist_roll` 4095;
  리더 암 2208~2681 카운트. 스트로크가 뚜렷하게 비대칭인 것은 정상입니다([05 영점 미세 조정](05-leader-digital-twin.md)에서 필요한 이유 참조).

# YOLO 추론 서버 (지성)

SmartFarm 작물 불량 판별용 YOLOv8 segmentation 추론 서버입니다.

---

## 전체 흐름 한눈에 보기

```
┌─────────────────────────────────────────────────────────────────────┐
│                           PC (Ubuntu)                               │
│                                                                     │
│  ┌──────────────────┐     ┌──────────────────┐  ┌───────────────┐  │
│  │  harvest_test.py │────▶│ vision_capture   │─▶│ infer_server  │  │
│  │  (Dobot ROS)     │5012 │ _daemon.py (지웅) │  │ .py (지성)    │  │
│  │  각도 0°→120°    │     │                  │  │ best.pt YOLO  │  │
│  │  →-120° 순 캡처  │◀────│ 3장 저장 완료 후 │◀─│ error 검출 시 │  │
│  │                  │판정 │ 추론 서버 호출   │  │ quality=error │  │
│  └──────────────────┘     └──────────────────┘  └───────────────┘  │
│         │                          ▲                   :5020        │
│         │ normal → 컨베이어         │                                │
│         │ error  → 불량품 상자      │ :5002                          │
│         ▼                          │                                │
│  ┌──────────────────┐              │                                │
│  │   Dobot 로봇     │              │                                │
│  └──────────────────┘              │                                │
└───────────────────────────────────┼────────────────────────────────┘
                                    │
                         ┌──────────┴──────────┐
                         │  라즈베리파이 5      │
                         │ raspi_jpeg_capture  │
                         │ _client.py          │
                         │ 카메라로 JPG 촬영   │
                         └─────────────────────┘
```

---

## 포트 정리

| 포트 | 연결 방향 | 역할 |
|------|-----------|------|
| **5002** | PC ← 라즈베리파이 | JPG 이미지 전송 |
| **5012** | PC 내부 (Dobot → daemon) | capture 요청 |
| **5020** | PC 내부 (daemon → 추론서버) | YOLO 추론 요청 |

---

## 사전 준비 (최초 1회만)

```bash
# 1. 지성 폴더에서 가상환경 생성
cd workspaces/지성/yolov_wait
python3 -m venv .venv
.venv/bin/pip install ultralytics

# 2. 지웅 폴더 venv 준비 (이미 있으면 생략)
cd workspaces/지웅/vision
python3 -m venv .venv
.venv/bin/pip install opencv-python numpy
```

---

## 실행 순서 (터미널 4개)

> **순서가 중요합니다.** 반드시 아래 순서대로 실행하세요.

---

### Step 1 — YOLO 추론 서버 실행 (지성, PC)

```bash
cd workspaces/지성/yolov_wait
bash run_infer_server.sh
```

**정상 출력:**
```
[infer] model loaded: best.pt, names={0: 'error'}
[infer] listening on 127.0.0.1:5020
```

> 이 터미널은 계속 열어두세요.

---

### Step 2 — 비전 캡처 데몬 실행 (지웅, PC)

> ⚠️ `vision_capture_daemon.py`에 `--infer-port 5020` 옵션이 추가된 버전이 필요합니다.  
> 지웅 팀원과 연동 작업 후 사용하세요. 현재 임시 실행 방법:

```bash
cd workspaces/지웅/vision
source .venv/bin/activate
python vision_capture_daemon.py \
  --pi-host 0.0.0.0 \
  --pi-port 5002 \
  --control-host 127.0.0.1 \
  --control-port 5012 \
  --save-dir incoming_jpegs
```

**정상 출력:**
```
[daemon] waiting for Raspberry Pi on 0.0.0.0:5002
```

> 라즈베리파이가 접속하기 전까지 여기서 대기합니다.

---

### Step 3 — 라즈베리파이 클라이언트 실행 (라즈베리파이)

> 라즈베리파이에서 실행합니다. `<PC_IP>` 를 실제 PC IP로 교체하세요.

```bash
python3 raspi_jpeg_capture_client.py \
  --server-host <PC_IP> \
  --server-port 5002 \
  --width 1280 \
  --height 720 \
  --quality 90 \
  --reconnect
```

**정상 출력 (PC 데몬 쪽):**
```
[daemon] Raspberry Pi connected: 192.168.x.x:xxxxx
[daemon] control listening on 127.0.0.1:5012, save_dir=...
```

---

### Step 4 — Dobot ROS 노드 실행 (PC)

```bash
cd workspaces/지웅/ros2_ws
source /opt/ros/humble/setup.bash
source ~/ros2/magician_ros2_control_system_ws/install/setup.bash
source install/setup.bash

ros2 run dobot_control_pkg harvest_test \
  --harvest-index 1 \
  --vision-mode socket \
  --vision-host 127.0.0.1 \
  --vision-port 5012
```

**수확 인덱스 선택 후 `s` 입력 → 동작 시작**

---

## 실행 후 예상 흐름

```
1. Dobot이 수확 위치로 이동 → 작물 흡착
2. 카메라 위치로 이동
3. 0° 회전 → capture 요청 → 라즈베리파이 JPG 전송 → 저장
4. 120° 회전 → capture 요청 → 라즈베리파이 JPG 전송 → 저장
5. -120° 회전 → capture 요청 → 라즈베리파이 JPG 전송 → 저장
6. [데몬] 3장 모두 저장됨 → 추론 서버(5020)에 경로 전송
7. [추론서버] YOLO 추론 실행
   - error 검출 없음 → quality_status = "normal"
   - error 검출됨   → quality_status = "error"
8. [Dobot]
   - normal → 컨베이어 시작점 이동 → 흡착 OFF
   - error  → 불량품 상자 이동 → 흡착 OFF
9. 홈 복귀
```

---

## 추론 결과 저장 위치

```
workspaces/지웅/vision/incoming_jpegs/
└── harvest_1_20260623_153000/
    ├── angle_000.jpg       ← 0° 촬영
    ├── angle_120.jpg       ← 120° 촬영
    ├── angle_-120.jpg      ← -120° 촬영
    └── capture_session.json ← 메타데이터 + 판정 결과
```

---

## 추론 서버 단독 테스트 (카메라 없이)

추론 서버가 정상 동작하는지 이미지 경로로 직접 확인:

```bash
cd workspaces/지성/yolov_wait
source .venv/bin/activate

python -c "
from infer_client import request_inference
result = request_inference(
    image_paths=[
        '/path/to/angle_000.jpg',
        '/path/to/angle_120.jpg',
        '/path/to/angle_-120.jpg',
    ],
    sequence_id='test_001',
    host='127.0.0.1',
    port=5020,
)
print('판정 결과:', result)
"
```

**출력 예:**
```
판정 결과: normal
# 또는
판정 결과: error
```

---

## 판정 기준

| 조건 | 결과 |
|------|------|
| 3장 중 1장이라도 `error` 클래스 검출 (conf ≥ 0.25) | `error` |
| 3장 모두 검출 없음 | `normal` |

confidence 임계값 변경은 `run_infer_server.sh` 의 `--conf` 값을 수정하세요.

---

## 지웅 팀원에게 — daemon 연동 방법

`vision_capture_daemon.py` 의 `save_capture_result()` 함수에서 3장 저장 후 아래 코드를 추가하면 됩니다:

```python
# infer_client.py 경로를 sys.path에 추가 후 import
import sys
sys.path.insert(0, '/path/to/workspaces/지성/yolov_wait')
from infer_client import request_inference, InferenceError

# save_capture_result() 내부에서 3장 완료 시 호출
try:
    quality = request_inference(
        image_paths=[str(saved_path)],   # 각 캡처마다 경로 수집
        sequence_id=sequence_id,
        host='127.0.0.1',
        port=5020,
    )
except InferenceError as e:
    quality = 'unknown'

# 기존 TEMPORARY_SUCCESS_QUALITY_STATUS 대신 quality 사용
```

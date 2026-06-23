# Dobot 비전 소켓 연동 계획

작성 시각: `2026-06-23 15:37:26 KST`
구현 반영: `2026-06-23 16:04:11 KST`
연결 안정화 수정: `2026-06-23 16:26:50 KST`

## 구현 상태

- 계획한 분리 구조를 구현했다.
- 추가된 핵심 파일은 `vision_socket_protocol.py`, `vision_capture_daemon.py`, `run_vision_capture_daemon.sh`, `vision_capture_client.py`이다.
- `harvest_test.py`는 `--vision-mode socket`에서 각도 `0/120/-120`별로 캡처 요청을 보내고, 3장 성공 시 임시 `normal` 판정을 받아 컨베이어로 이동한다.
- 검증은 mock Pi 클라이언트 기반 `ros2 run ... --dry-run --vision-mode socket`까지 통과했다.
- 라즈베리파이 클라이언트가 Dobot 이동 중 명령 대기 timeout으로 연결을 끊는 문제를 수정했다. 기본 명령 대기는 무제한이며, 데몬은 Pi 소켓 끊김 시 새 연결을 한 번 받아 같은 요청을 재시도한다.

## 목표

Dobot이 촬영 위치에 도달하고 석션컵 각도를 `0도 -> 120도 -> -120도`로 변경할 때마다, 라즈베리파이에 **JPG 한 장 캡처 명령**을 소켓 통신으로 전달한다. 단, `harvest_test.py`가 비전 소켓 프로토콜까지 직접 떠안지 않도록 역할을 분리한다.

## 현재 확인한 비전 소켓 구조

비전 작업 경로: `/home/ssafy/work/SmartFarmProject/workspaces/지웅/vision`

현재 README 기준 핵심 구조:

- PC 서버: `pc_jpeg_capture_server.py`
  - TCP `:5002`에서 라즈베리파이 클라이언트 접속 대기
  - 라즈베리파이에 line-delimited JSON `capture` 명령 전송
  - 라즈베리파이에서 JPG 바이너리 패킷 수신
  - `incoming_jpegs/`에 JPG와 `latest_jpeg.json` 저장
- 라즈베리파이 클라이언트: `raspi_jpeg_capture_client.py`
  - PC 서버에 접속
  - `capture` 명령을 받으면 `rpicam-still`/`rpicam-jpeg`로 JPG 촬영
  - 메타데이터 + JPG bytes를 PC로 응답
- 프로토콜:
  - 명령: JSON line
  - 응답: `SFJ1` magic + metadata length + payload length + metadata JSON + JPG payload

## 문제 인식

`harvest_test.py`에 소켓 서버/클라이언트/패킷 저장/재시도 로직을 직접 넣으면 다음 문제가 생긴다.

1. Dobot 모션 코드와 비전 통신 코드가 섞여 유지보수가 어려워진다.
2. ROS 2 액션/서비스 오류와 카메라 소켓 오류가 한 파일에 뒤섞인다.
3. 라즈베리파이 연결 대기, 재연결, 캡처 저장 경로 관리가 Dobot 테스트 노드의 책임이 되어버린다.
4. 나중에 비전 추론/결과 판정까지 붙을 때 `harvest_test.py`가 너무 커진다.

## 권장 아키텍처

`harvest_test.py`는 **촬영 요청만 보내고 결과 경로만 받는 얇은 클라이언트**로 유지한다.

```text
Dobot ROS 2 노드
  harvest_test.py
    - Dobot 이동/석션/회전만 담당
    - 각도 도달 후 VisionCaptureClient.capture(...) 호출
              |
              | localhost JSON socket
              v
PC 비전 캡처 데몬
  vision_capture_daemon.py 신규
    - 라즈베리파이 접속 유지
    - harvest_test.py의 로컬 캡처 요청 수신
    - 라즈베리파이에 capture 명령 전달
    - JPG 수신/저장
    - 저장 경로와 메타데이터를 harvest_test.py에 응답
              |
              | TCP :5002, 기존 JPG 프로토콜
              v
Raspberry Pi
  raspi_jpeg_capture_client.py 기존 유지
    - capture 명령 수신
    - rpicam-still/rpicam-jpeg 촬영
    - JPG bytes 응답
```

## 파일 분리 계획

### 1. 비전 프로토콜 공통 모듈 생성

위치:

`workspaces/지웅/vision/vision_socket_protocol.py`

역할:

- `MAGIC`, `HEADER_STRUCT`, `recv_exact()`
- `read_jpeg_packet()`
- `send_json_line()`
- 필요 시 `write_jpeg_packet()`

이렇게 하면 `pc_jpeg_capture_server.py`, 새 데몬, 테스트 코드가 패킷 처리 로직을 중복하지 않는다.

### 2. PC 비전 캡처 데몬 추가

위치:

`workspaces/지웅/vision/vision_capture_daemon.py`

역할:

- 라즈베리파이 클라이언트 접속 대기: 기본 `0.0.0.0:5002`
- Dobot/ROS 측 로컬 요청 대기: 기본 `127.0.0.1:5012`
- 로컬 요청 예시:

```json
{
  "type": "capture",
  "sequence_id": "harvest_1_20260623_153000",
  "harvest_index": 1,
  "angle_deg": 0,
  "width": 1280,
  "height": 720,
  "quality": 90,
  "timeout_ms": 800
}
```

- 라즈베리파이로 전달할 기존 명령 예시:

```json
{
  "type": "capture",
  "request_id": "harvest_1_angle_000_20260623_153000",
  "width": 1280,
  "height": 720,
  "quality": 90,
  "timeout_ms": 800
}
```

- Dobot/ROS 측 응답 예시:

```json
{
  "status": "ok",
  "request_id": "harvest_1_angle_000_20260623_153000",
  "saved_path": "/home/ssafy/work/SmartFarmProject/workspaces/지웅/vision/incoming_jpegs/harvest_1_20260623_153000/angle_000.jpg",
  "angle_deg": 0,
  "harvest_index": 1,
  "payload_bytes": 123456,
  "metadata": {
    "sender": "raspberry-pi5",
    "camera_model": "Raspberry Pi Camera Module 3 Wide"
  }
}
```

### 3. Dobot ROS 패키지 안에는 얇은 클라이언트만 추가

위치:

`workspaces/지웅/ros2_ws/src/dobot_control_pkg/dobot_control_pkg/vision_capture_client.py`

역할:

- `VisionCaptureClient(host, port, timeout_sec)`
- `capture(sequence_id, harvest_index, angle_deg) -> CaptureResult`
- 표준 라이브러리 `socket`, `json`만 사용
- 라즈베리파이 프로토콜 세부사항은 모르게 한다.

### 4. `harvest_test.py`는 최소 수정

수정 방향:

- 기존 모션/석션/홈 복귀 흐름은 유지
- CLI 옵션만 추가

```text
--vision-mode wait|socket|off
--vision-host 127.0.0.1
--vision-port 5012
--vision-timeout-sec 10
--capture-width 1280
--capture-height 720
--capture-quality 90
```

권장 기본값:

- 개발 중 기본: `--vision-mode wait`
  - 현재처럼 각도별 2초 대기
  - 라즈베리파이 없이 Dobot 단독 테스트 가능
- 실제 촬영 통합 시: `--vision-mode socket`
  - 각도 도달 후 데몬에 캡처 요청

`run_sequence()` 안에서는 아래 한 줄 수준으로만 보이게 한다.

```python
vision_capture.capture(sequence_id, harvest_target.index, angle)
```

즉, `harvest_test.py`는 “언제 찍을지”만 알고, “어떻게 소켓으로 찍는지”는 모르게 한다.

## 실행 흐름 계획

### PC 쪽

```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/vision
source .venv/bin/activate
python vision_capture_daemon.py \
  --pi-host 0.0.0.0 \
  --pi-port 5002 \
  --control-host 127.0.0.1 \
  --control-port 5012 \
  --save-dir incoming_jpegs
```

### 라즈베리파이 쪽

```bash
cd ~/smartfarm_vision_socket
python3 raspi_jpeg_capture_client.py \
  --server-host <PC_IP> \
  --server-port 5002 \
  --width 1280 \
  --height 720 \
  --quality 90 \
  --camera-timeout-ms 800 \
  --reconnect
```

### Dobot 쪽

```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/ros2_ws
source /opt/ros/humble/setup.bash
source /home/ssafy/ros2/magician_ros2_control_system_ws/install/setup.bash
source install/setup.bash

ros2 run dobot_control_pkg harvest_test \
  --harvest-index 1 \
  --vision-mode socket \
  --vision-host 127.0.0.1 \
  --vision-port 5012
```

## 구현 단계

### 단계 1. 현재 비전 소켓 프로토콜을 공통 모듈로 분리

- `pc_jpeg_capture_server.py`에서 중복 가능한 프로토콜 함수를 `vision_socket_protocol.py`로 이동
- 기존 `smoke_jpeg_command.sh`가 계속 통과하는지 확인

검증:

```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/vision
python3 -m py_compile vision_socket_protocol.py pc_jpeg_capture_server.py raspi_jpeg_capture_client.py
bash smoke_jpeg_command.sh
```

### 단계 2. `vision_capture_daemon.py` 작성

- Pi 연결 수신 스레드
- 로컬 제어 요청 수신 스레드 또는 순차 루프
- 캡처 요청은 한 번에 하나만 처리하도록 lock 적용
- JPG 저장 시 `sequence_id/angle_000.jpg`, `angle_120.jpg`, `angle_-120.jpg` 형태로 저장

검증:

- Pi 없이 mock client로 1장 캡처
- mock client로 3장 연속 캡처
- `latest_jpeg.json` 또는 별도 `capture_session.json` 생성 확인

### 단계 3. `vision_capture_client.py` 작성

- Dobot ROS 패키지 내부에서 로컬 데몬에 JSON 요청을 보내는 얇은 클라이언트
- 에러 시 명확한 예외 메시지 제공
- dry-run/비전 미사용 모드에서는 네트워크를 열지 않음

검증:

```bash
python3 -m py_compile workspaces/지웅/ros2_ws/src/dobot_control_pkg/dobot_control_pkg/vision_capture_client.py
```

### 단계 4. `harvest_test.py`에 캡처 전략 주입

- 기존 `wait(wait_sec, temporary vision wait...)` 위치를 캡처 전략 호출로 교체
- `wait` 모드: 기존 2초 대기 유지
- `socket` 모드: 데몬에 캡처 요청
- `off` 모드: 촬영 없이 바로 다음 각도로 진행

검증:

```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/ros2_ws
python3 -m py_compile src/dobot_control_pkg/dobot_control_pkg/harvest_test.py
colcon build --packages-select dobot_control_pkg
ros2 run dobot_control_pkg harvest_test --dry-run --harvest-index 1 --yes --vision-mode wait --wait-sec 0.01
```

### 단계 5. 통합 스모크 테스트

- PC 데몬 실행
- mock Pi 클라이언트 실행
- Dobot dry-run + socket mode 실행
- 0/120/-120 3장 저장 확인

성공 기준:

- `incoming_jpegs/<sequence_id>/` 아래 JPG 3장 생성
- 각 파일이 `harvest_index`, `angle_deg`, `request_id`와 연결됨
- `harvest_test.py` 로그에 각도별 캡처 성공 경로 출력

### 단계 6. 실제 하드웨어 테스트

- 라즈베리파이 실제 카메라 클라이언트 실행
- Dobot 실제 동작 실행
- 촬영 위치 각도별 3장 저장 확인
- 파일명/메타데이터가 나중에 비전 추론과 연결 가능한지 확인

## 에러 처리 정책

초기 MVP에서는 보수적으로 처리한다.

- `--vision-mode socket`에서 캡처 실패 시 기본은 시퀀스 중단
- 옵션으로 나중에 `--continue-on-capture-error`를 추가할 수 있음
- 실패 시 석션을 켠 채 멈추는 상황을 피하기 위해 최종적으로는 안전 복귀/석션 OFF 정책도 정해야 함

## 결정이 필요한 항목

1. 실제 통합에서 캡처 실패 시 즉시 중단할지, 해당 각도만 건너뛰고 진행할지
2. 사진 저장 경로를 `vision/incoming_jpegs/<sequence_id>/`로 둘지, 추후 데이터셋 경로로 바로 보낼지
3. 첫 MVP에서 `0/120/-120` 3장을 모두 찍은 뒤 비전 판정을 할지, 각도별로 즉시 판정을 붙일지
4. 라즈베리파이 클라이언트는 계속 PC 서버에 붙어 대기하는 daemon 형태로 둘지, 테스트 때마다 수동 실행할지

## 권장 결정안

- 캡처 실패 시: **즉시 중단**
- 저장 경로: 우선 `vision/incoming_jpegs/<sequence_id>/`
- 판정 방식: 우선 3장 저장만 완료하고, 판정은 다음 단계에서 연결
- 라즈베리파이: `--reconnect` 옵션으로 계속 대기
- `harvest_test.py`: 모션 제어 + 캡처 요청 타이밍만 담당
- 비전 소켓 상세: `vision_capture_daemon.py`가 담당

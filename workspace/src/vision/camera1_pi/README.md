# SmartFarmProject Vision Socket Prototype

라즈베리파이5 + Raspberry Pi Camera Module 3 Wide에서 짧은 영상을 촬영하고, 소켓 통신으로 PC에 전달한 뒤 PC에서 받은 영상을 **OpenCV `imshow` 창으로 바로 확인**할 수 있게 하는 1차 테스트 코드입니다. 필요하면 같은 수신기에서 HTTP 확인도 같이 사용할 수 있습니다.

## 파일 구성

- `raspi_capture_send.py`
  라즈베리파이에서 실행. 카메라 연결 확인 → 영상 촬영 → PC TCP 서버로 영상 전송.
- `pc_receiver_streamer.py`
  PC에서 실행. TCP로 영상 수신 → 파일 저장 → OpenCV `imshow` 창 재생. 옵션으로 HTTP latest 영상 송출도 가능.
- `pc_jpeg_capture_server.py`
  PC에서 실행. 라즈베리파이 클라이언트에 `capture` 명령을 보내고, 응답으로 JPG 한 장을 수신/저장/표시.
- `vision_capture_daemon.py`
  PC에서 실행. Dobot ROS 노드의 로컬 캡처 요청을 받아 라즈베리파이 클라이언트에 전달하고, JPG 수신 성공 시 임시 `normal` 판정 결과를 반환.
- `vision_socket_protocol.py`
  JSON line 명령과 `SFJ1` JPG 패킷을 처리하는 공통 소켓 프로토콜 모듈.
- `run_vision_capture_daemon.sh`
  Dobot 연동용 PC 비전 캡처 데몬 권장 실행 스크립트.
- `raspi_jpeg_capture_client.py`
  라즈베리파이에서 실행. PC 소켓 서버에 연결해 대기하다가 `capture` 명령을 받으면 JPG 한 장을 촬영해 서버로 전송.
- `run_pc_jpeg_capture_server.sh`
  PC JPG 캡처 서버를 OpenCV 표시 모드로 실행하는 권장 스크립트.
- `smoke_jpeg_command.sh`
  카메라 없이 PC 내부에서 `서버 명령 → 클라이언트 mock JPG 응답` 흐름 검증.
- `smoke_local_transfer.sh`
  카메라 없이 PC 내부에서 더미/테스트 영상을 만들어 소켓 전송을 검증.
- `.venv/`
  PC 수신기에서 OpenCV 표시를 위해 `opencv-python`, `numpy`를 설치한 로컬 가상환경.

## 통신 구조

```text
Raspberry Pi 5
  raspi_capture_send.py
    1. rpicam-hello/libcamera-hello --list-cameras
    2. rpicam-vid/libcamera-vid 로 .h264 촬영
    3. TCP socket으로 PC에 파일 전송

PC
  pc_receiver_streamer.py
    1. TCP :5001 에서 영상 수신
    2. incoming_videos/ 에 저장
    3. 필요 시 ffmpeg로 .mp4 remux
    4. OpenCV imshow 창으로 재생
    5. 옵션으로 HTTP :8000 에서 latest 영상 확인

요청-응답형 JPG 캡처
  PC pc_jpeg_capture_server.py
    1. TCP :5002 에서 라즈베리파이 클라이언트 접속 대기
    2. 클라이언트에 JSON capture 명령 전송
    3. JPG 바이너리 응답 수신
    4. incoming_jpegs/ 에 저장하고 OpenCV imshow로 표시

  Raspberry Pi raspi_jpeg_capture_client.py
    1. PC 소켓 서버에 연결
    2. capture 명령 대기
    3. rpicam-still/rpicam-jpeg 로 JPG 한 장 촬영
    4. 인코딩된 JPG bytes를 PC 서버에 전송

Dobot 연동형 3장 캡처
  Dobot harvest_test.py
    1. 촬영 위치에서 0/120/-120도 각도 도달
    2. localhost:5012 의 vision_capture_daemon.py 에 capture 요청

  PC vision_capture_daemon.py
    1. 라즈베리파이 클라이언트 연결 유지
    2. Dobot 요청을 Raspberry Pi capture 명령으로 변환
    3. 각도별 JPG를 incoming_jpegs/<sequence_id>/angle_*.jpg 로 저장
    4. 현재 테스트 목적상 3장 수신 성공 시 normal 판정 응답
```

## PC에서 먼저 실행

PC IP 후보는 현재 환경 기준 `192.168.110.109` 입니다. 라즈베리파이와 같은 네트워크에서 접근 가능한 IP를 사용하세요.

### OpenCV 창으로 바로 보기

권장 실행 방식:

```bash
cd ~/work/SmartFarmProject/workspaces/지웅/vision
bash run_pc_receiver_opencv.sh
```

직접 실행이 필요하면:

```bash
cd ~/work/SmartFarmProject/workspaces/지웅/vision
source .venv/bin/activate
python pc_receiver_streamer.py \
  --host 0.0.0.0 \
  --transfer-port 5001 \
  --http-port 8000 \
  --save-dir incoming_videos \
  --show-window
```

- 수신이 끝나면 OpenCV `imshow` 창에서 영상이 재생됩니다.
- 창에서 `q`를 누르면 현재 클립 재생을 멈춥니다.
- `run_pc_receiver_opencv.sh`는 OpenCV Qt font 경고를 줄이기 위해 시스템 DejaVu 폰트 디렉터리를 자동 연결합니다.
- `tcsetattr: Inappropriate ioctl for device` 메시지는 **백그라운드/비대화형 실행에서 종료할 때** 나올 수 있는 터미널 경고라서, 실제 영상 수신과 재생 성공 자체와는 별개입니다. 평소에는 **포그라운드 실행**을 권장합니다.

### HTTP 확인까지 같이 쓰기

위 명령은 OpenCV 창 + HTTP 확인을 동시에 켭니다.

확인 URL:

- `http://<PC_IP>:8000/`
- `http://<PC_IP>:8000/latest`
- `http://<PC_IP>:8000/metadata`

## 요청-응답형 JPG 한 장 캡처

이번 구조는 **PC가 소켓 서버**, 라즈베리파이가 **소켓 클라이언트**입니다. 라즈베리파이는 서버에 연결해 대기하고, PC 서버가 `capture` 명령을 보내면 JPG 한 장을 찍어서 인코딩된 JPG bytes를 다시 보냅니다.

### PC 서버 실행

```bash
cd ~/work/SmartFarmProject/workspaces/지웅/vision
bash run_pc_jpeg_capture_server.sh
```

수동으로 여러 번 찍고 싶으면 서버 터미널에서 Enter를 누릅니다.

자동 1회 테스트용:

```bash
cd ~/work/SmartFarmProject/workspaces/지웅/vision
source .venv/bin/activate
python pc_jpeg_capture_server.py \
  --host 0.0.0.0 \
  --port 5002 \
  --save-dir incoming_jpegs \
  --auto-capture \
  --count 1 \
  --width 1280 \
  --height 720 \
  --quality 90
```

### 라즈베리파이 클라이언트 실행

```bash
cd ~/smartfarm_vision_socket
python3 raspi_jpeg_capture_client.py \
  --server-host 192.168.110.109 \
  --server-port 5002 \
  --width 1280 \
  --height 720 \
  --quality 90 \
  --camera-timeout-ms 800
```

성공하면 PC의 `incoming_jpegs/` 아래에 `.jpg` 파일과 `latest_jpeg.json`이 생깁니다.

## Dobot 연동형 3장 캡처

이 방식은 `harvest_test.py`가 촬영 각도 `0/120/-120`에 도달할 때마다 PC 비전 데몬에 캡처 요청을 보내는 구조입니다. `harvest_test.py`에는 소켓 서버/패킷 저장 로직을 넣지 않고, 얇은 로컬 클라이언트만 둡니다.

### PC 비전 데몬 실행

```bash
cd ~/work/SmartFarmProject/workspaces/지웅/vision
bash run_vision_capture_daemon.sh
```

직접 실행:

```bash
cd ~/work/SmartFarmProject/workspaces/지웅/vision
source .venv/bin/activate
python vision_capture_daemon.py \
  --pi-host 0.0.0.0 \
  --pi-port 5002 \
  --control-host 127.0.0.1 \
  --control-port 5012 \
  --save-dir incoming_jpegs
```

### 라즈베리파이 클라이언트 실행

```bash
cd ~/smartfarm_vision_socket
python3 raspi_jpeg_capture_client.py \
  --server-host 192.168.110.109 \
  --server-port 5002 \
  --width 1280 \
  --height 720 \
  --quality 90 \
  --camera-timeout-ms 800 \
  --reconnect
```

주의: Dobot이 수확 위치에서 촬영 위치까지 이동하는 동안 라즈베리파이 클라이언트는 PC 데몬 명령을 오래 기다릴 수 있어야 합니다. 현재 기본값은 `--command-idle-timeout-sec 0`이라 명령 대기 중 timeout 없이 계속 기다립니다. 구버전 클라이언트를 라즈베리파이에 복사해 둔 경우 최신 `raspi_jpeg_capture_client.py`로 다시 복사해야 합니다.

라즈베리파이에 최신 클라이언트 복사 예시:

```bash
scp ~/work/SmartFarmProject/workspaces/지웅/vision/raspi_jpeg_capture_client.py \
  ssafy@<RASPBERRY_PI_IP>:~/smartfarm_vision_socket/raspi_jpeg_capture_client.py
```

### Dobot 테스트 노드 실행

```bash
cd ~/work/SmartFarmProject/workspaces/지웅/ros2_ws
source /opt/ros/humble/setup.bash
source ~/ros2/magician_ros2_control_system_ws/install/setup.bash
source install/setup.bash

ros2 run dobot harvest_test \
  --harvest-index 1 \
  --vision-mode socket \
  --vision-host 127.0.0.1 \
  --vision-port 5012
```

성공하면 `incoming_jpegs/<sequence_id>/` 아래에 아래 3장이 저장됩니다.

- `angle_000.jpg`
- `angle_120.jpg`
- `angle_-120.jpg`

현재는 테스트 목적상 3장 모두 수신하면 `quality_status=normal`을 Dobot 노드에 반환합니다. Dobot 노드는 이 판정에 따라 정상은 컨베이어 시작점, 불량은 불량품 상자로 이동합니다. 추후 OpenCV/YOLO 추론은 `vision_capture_daemon.py`에서 `quality_status`를 산출하도록 확장합니다.

## 라즈베리파이에서 실행

라즈베리파이로 파일을 복사한 뒤 실행합니다.

```bash
python3 raspi_capture_send.py \
  --pc-host 192.168.110.109 \
  --pc-port 5001 \
  --duration 5 \
  --width 1280 \
  --height 720 \
  --fps 30
```

Bookworm 계열 라즈비안에서는 `rpicam-hello`, `rpicam-vid`가 기본입니다. 구버전에서는 `libcamera-hello`, `libcamera-vid`를 자동으로 찾습니다.

## 로컬 스모크 테스트

요청-응답형 JPG 캡처 프로토콜 검증:

```bash
cd ~/work/SmartFarmProject/workspaces/지웅/vision
bash smoke_jpeg_command.sh
```

카메라 없이 PC에서 영상 파일 전송 프로토콜만 검증:

```bash
cd ~/work/SmartFarmProject/workspaces/지웅/vision
bash smoke_local_transfer.sh
```

성공하면 `incoming_videos/latest.json`과 수신 영상 파일이 생성되고, `http://127.0.0.1:8000/metadata`가 응답합니다.

## 포트

- TCP 파일 수신: `5001`
- 요청-응답형 JPG / 라즈베리파이 클라이언트 접속: `5002`
- Dobot 로컬 캡처 요청: `5012`
- HTTP 송출: `8000`

방화벽이 켜져 있으면 PC에서 위 포트를 열어야 합니다.

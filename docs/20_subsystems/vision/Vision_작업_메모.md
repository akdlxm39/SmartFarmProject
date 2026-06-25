# SmartFarmProject Vision 작업 메모

작성일: 2026-06-23
범위: 이 문서는 이 쓰레드에서 집중 관리할 **비전/카메라/AI 추론 파트**의 실행 메모다.

## 1. 현재 문서 검토 기준
검토한 문서:
- `README.md`
- `docs/진행_로그.md`
- `docs/작업_결정_메모.md`
- `docs/R&R_초안.md`
- `docs/WBS_재검토_메모.md`
- `references/WBS.xlsx`
- `docs/시스템_데이터_흐름_초안.md`

## 2. 이 쓰레드의 집중 범위
이 쓰레드에서는 **비전 파트만 집중**해서 정리한다.

### 직접 다룰 것
- 1번 카메라 메인 판정 파이프라인
- 2번 카메라 컨베이어 흐름 확인 파이프라인
- 데이터셋 수집/라벨링 기준
- YOLO 계열 모델 학습/추론 구조
- 라즈베리파이 또는 PC 추론 배치 판단
- 비전 결과 메시지/로그 포맷
- Dobot/컨베이어/서버와의 인터페이스 중 비전 결과에 직접 연결되는 부분

### 인터페이스 수준에서만 언급할 것
- Dobot 좌표/동작 시퀀스 자체
- 컨베이어 모터 제어 상세
- TurtleBot SLAM/배송 구현
- Django/Vue 화면 구현 상세

## 3. 현재 확정된 비전 역할
### 3.1 1번 카메라 — 메인 판정 카메라
입력:
- Dobot 석션컵에 흡착된 작물
- 0도/120도/-120도 3방향 이미지

주요 기능:
- 작물 종류 3종 분류
- 정상/불량, 특히 썩음 여부 판별
- 판정 결과를 Dobot 제어와 서버 로그에 전달

현재 판단:
- 1번 카메라는 다각도 촬영이 가능하므로 **최종 판정의 권위 소스(authoritative source)**로 둔다.
- 불량 판정이 나오면 작물은 컨베이어에 올라가지 않고 Dobot이 별도 상자에 넣는다.

### 3.2 2번 카메라 — 보조 비전/흐름 확인 카메라
입력:
- 컨베이어 위 정상 작물의 이동 영상

주요 기능:
- 작물 존재 여부 확인
- 벨트 위 위치/타이밍 확인
- 컨베이어 흐름 이상 감지
- 벨트 끝 도달 또는 누락/이탈 이벤트 기록

현재 판단:
- 2번 카메라는 메인 분류를 반복하지 않고, **이송 상태 검증과 예외 감지**에 집중한다.
- 필요 시 2번 카메라에서 간단한 객체 검출/트래킹만 수행한다.

## 4. WBS/R&R 기준 비전 관련 작업
### WBS에서 연결되는 항목
- `AI / 데이터 기획`: 작물 이미지 수집 계획 및 라벨링 기준 수립
- `AI / AI 모델링`: 데이터셋 수집, YOLO 모델 학습, 라즈베리파이 엣지 포팅
- `AI / 비전 제어`: OpenCV 프레임 전처리 및 실시간 추론 파이프라인 구축
- `임베디드 / HW 세팅(2)`: 라즈베리파이, RGB-D 카메라, 압력센서 회로 구성
- `임베디드 / 장치 제어`: RGB-D 객체 인식 기반 컨베이어 구동/정지 및 적재 로직
- `공통 / 시스템 연동`: AI 판별 결과를 ROS Bridge 등으로 서버에 전송

### R&R에서 연결되는 책임
- Participant1: 비전/임베디드 리드
- 주요 산출물: 데이터셋 구조, 라벨링 기준, YOLO 학습 결과, 추론 파이프라인 코드, 카메라별 입출력 명세
- 주요 의존성:
  - Dobot 촬영 포즈/트리거는 Participant2와 협의
  - 비전 결과 로그/API 포맷은 Participant3와 협의

## 5. 우선 설계해야 할 데이터 포맷 초안
작물 1개 기준 최소 비전 결과:

```json
{
  "inspection_id": "string",
  "timestamp": "ISO-8601",
  "camera_id": "camera1",
  "image_set": ["0deg", "120deg", "240deg"],
  "crop_type": "crop_a | crop_b | crop_c | unknown",
  "quality_status": "normal | defect | unknown",
  "defect_type": "rot | damage | none | unknown",
  "confidence": 0.0,
  "decision_source": "camera1_main",
  "next_action": "to_conveyor | to_defect_box | retry_capture | manual_check"
}
```

2번 카메라 이벤트 초안:

```json
{
  "inspection_id": "string",
  "camera_id": "camera2",
  "object_detected": true,
  "belt_position": "entry | middle | exit | unknown",
  "event_type": "entered | moving | exited | missing | misaligned",
  "transport_status": "in_progress | delivered | abnormal"
}
```

## 6. 비전 파트 우선 작업 순서
1. 작물 3종 이름과 불량/썩음 기준 확정
2. 1번 카메라 3방향 촬영 이미지 저장 구조 정의
3. 데이터셋 폴더 구조와 라벨링 규칙 결정
4. 1차 학습 기준 모델 선택: YOLO 검출/분류 중 어떤 방식으로 갈지 결정
5. PC에서 먼저 추론 파이프라인 검증
6. 라즈베리파이에서 추론 속도/메모리 검증
7. 2번 카메라는 객체 존재/위치/타이밍 감지부터 구현
8. ROS/서버로 넘길 비전 결과 메시지 포맷 확정

## 7. 지금 필요한 확인 질문
- 실제 작물 3종은 무엇인가?
- 불량 기준은 `썩음`만 볼 것인가, 흠집/크기/색 이상도 포함할 것인가?
- 1번 카메라 3방향 이미지는 Dobot 자세 변경으로 얻을 것인가, 별도 회전 지그로 얻을 것인가?
- 1차 구현은 PC 추론으로 검증한 뒤 라즈베리파이로 이관할 것인가?
- RGB-D 카메라의 depth 정보는 2번 카메라 흐름 확인에 꼭 사용할 것인가, RGB만으로 MVP를 갈 것인가?

## 8. 라즈베리파이 카메라 소켓 전송 1차 테스트
작업 경로:
- `workspaces/지웅/vision`

작성한 코드:
- `workspaces/지웅/vision/raspi_capture_send.py`
  - 라즈베리파이5에서 카메라 연결 확인
  - `rpicam-vid` 또는 `libcamera-vid`로 H.264 영상 촬영
  - TCP 소켓으로 PC에 영상 파일 전송
- `workspaces/지웅/vision/pc_receiver_streamer.py`
  - PC에서 TCP 소켓으로 영상 수신
  - `incoming_videos/`에 파일 저장
  - HTTP `:8000`으로 latest 영상/metadata 송출
- `workspaces/지웅/vision/smoke_local_transfer.sh`
  - 카메라 없이 로컬에서 소켓 프로토콜 검증

현재 통신 포트:
- TCP 영상 수신: `5001`
- HTTP 영상 송출: `8000`

실제 확인 결과:
- 로컬 PC 내부 더미 영상 전송 테스트 성공
- 라즈베리파이 SSH 접속 성공: `ssafy@192.168.110.137`
- 라즈베리파이 Python 확인: `Python 3.13.5`
- 라즈베리파이 카메라 앱 확인: `/usr/bin/rpicam-hello`, `/usr/bin/rpicam-vid`
- 카메라 목록 확인 성공: `imx708_wide_noir` / 4608x2592 Camera Module 3 Wide 계열로 인식됨
- 라즈베리파이에서 mock 파일을 PC로 소켓 전송하는 테스트 성공
- PC HTTP endpoint 확인 성공: `/metadata`, `/latest`
- 재시도 결과 실제 `rpicam-vid` 2초 촬영 + 라즈베리파이→PC 소켓 전송 성공
- 수신 파일 검증 결과: `1280x720`, 약 `1.67초`, `51프레임`, H.264 High profile
- PC 로컬 `.venv`에 `opencv-python`, `numpy`를 설치했고, 수신 파일을 remux 후 OpenCV `VideoCapture`로 첫 프레임 읽기 성공
- `pc_receiver_streamer.py --show-window` 모드에서 수신 후 `.mp4` remux 파일 생성까지 확인했으며, PC GUI에서는 OpenCV `imshow` 창 재생 방식으로 사용할 수 있다.

현재 상태:
- 소켓 통신, 실제 카메라 촬영, PC 수신 저장은 모두 성공했다.
- 이후 PC 확인 방식은 HTTP보다 OpenCV `imshow` 창 기반을 기본으로 가져가면 된다.
- OpenCV Qt font 경고는 `.venv` 내부 `cv2/qt/fonts` 디렉터리가 없어서 발생한 것이고, `run_pc_receiver_opencv.sh`에서 시스템 DejaVu 폰트 경로를 연결/설정해 완화했다.
- `tcsetattr: Inappropriate ioctl for device` 메시지는 백그라운드/비대화형 종료 시 나타날 수 있는 터미널 경고로, 영상 수신/재생 성공과는 별개다. 실제 사용은 포그라운드 실행을 권장한다.

## 9. 요청-응답형 JPG 한 장 캡처 구조
새 요구사항:
- 소켓 통신은 유지한다.
- PC 소켓 서버가 라즈베리파이에 `capture` 메시지를 보낸다.
- 라즈베리파이는 메시지를 받으면 사진 한 장, 즉 한 프레임을 JPG로 촬영한다.
- 라즈베리파이는 인코딩된 JPG bytes를 다시 PC 소켓 서버로 전송한다.

추가한 코드:
- `workspaces/지웅/vision/pc_jpeg_capture_server.py`
  - PC 소켓 서버
  - 라즈베리파이 클라이언트 접속 대기
  - JSON `capture` 명령 전송
  - JPG 바이너리 응답 수신/저장
  - OpenCV `imshow` 표시 지원
- `workspaces/지웅/vision/raspi_jpeg_capture_client.py`
  - 라즈베리파이 소켓 클라이언트
  - PC 서버에 연결 후 명령 대기
  - `rpicam-still`/`rpicam-jpeg`로 JPG 한 장 촬영
  - JPG bytes를 PC 서버로 전송
- `workspaces/지웅/vision/run_pc_jpeg_capture_server.sh`
  - PC JPG 캡처 서버 실행 스크립트
- `workspaces/지웅/vision/smoke_jpeg_command.sh`
  - 로컬 mock JPG로 `서버 명령 → 클라이언트 응답 → 서버 저장` 검증

검증 결과:
- 로컬 mock 테스트 성공: 서버가 capture 명령을 보내고 mock 클라이언트가 JPG bytes를 응답, PC에서 OpenCV 디코딩 성공
- 라즈베리파이 실제 테스트 성공:
  - PC 서버가 `capture` 명령 전송
  - 라즈베리파이가 `rpicam-still`로 JPG 촬영
  - 라즈베리파이가 PC로 JPG bytes 전송
  - PC가 `incoming_jpegs_pi/`에 JPG 저장
  - PC OpenCV 디코딩 결과 `720x1280x3` 확인
- 실제 수신 파일 예시:
  - `incoming_jpegs_pi/20260623_140234_req_20260623_140233_291550.jpg`
  - payload bytes: `158287`
  - metadata: `1280x720`, quality `90`, source `rpicam`

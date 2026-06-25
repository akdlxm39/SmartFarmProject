# Conveyor ROI + Modbus 구현 계획

작성일: 2026-06-24
대상 샘플: `references/realsense-test-image.png`
범위: D435i/RealSense ROS 입력 → 컨베이어 단일 ROI 설정 → 빨간색/녹색 큐브 감지 → 큐브가 ROI에서 사라질 때까지 Raspberry Pi Modbus 기반 컨베이어 구동 → 추후 웹 표시 연동

> 이 계획은 컨베이어 파트만 다룬다. 1번 카메라의 작물 종류/정상·불량 판정은 권위 소스로 유지하고, 컨베이어 카메라는 **컨베이어 위 빨간색/녹색 큐브 존재 여부와 이송 완료 여부** 확인에 집중한다.


## 0. 2026-06-24 비동기 Modbus / Raspberry Pi 5 전환 업데이트

사용자 피드백에 따라 기존 동기식 Modbus client write/read 구조는 버벅임을 유발할 수 있으므로, Modbus 기준 버전을 **`pymodbus==3.13.1`**로 올리고 async 구조로 전환한다.

새 계획:
- Modbus TCP server는 `192.168.110.109:50200`의 외부/shared register layer로 둔다.
- Raspberry Pi 5/Raspbian은 **Modbus client + 컨베이어 GPIO 모터 제어**를 담당한다.
- PC/ROS2의 D435i/OpenCV 노드도 Modbus client이며, 비전 처리와 상태 생성만 담당하고 Modbus I/O는 `AsyncModbusTcpClient` 기반 별도 worker로 분리한다.
- ROS image callback 안에서 네트워크 write/read를 기다리지 않는다.
- Pi가 `40023 conveyor_status`, `40024 conveyor_error_code`를 실제 모터 기준으로 갱신하고, PC는 `40021/40022/40025/40026/40027` 중심으로 쓴다.
- 상세 전환 계획은 `docs/Conveyor_Modbus_Async_RaspberryPi_전환_계획.md`, server 전용 메모는 `docs/Conveyor_Modbus_Server_작업_메모.md`에 둔다.

## 1. 요구사항 업데이트

사용자 피드백 기준으로 계획을 단순화한다.

- 감지 대상은 작물이 아니라 **컨베이어 위에 올라온 빨간색/녹색 큐브**다.
- ROI를 `entry/middle/exit`로 나누지 않는다.
- 컨베이어 전체 또는 벨트 영역을 **단일 `conveyor_roi`**로 잡는다.
- `conveyor_roi` 안에서 빨간색/녹색 큐브가 감지되면 컨베이어를 움직인다.
- 빨간 큐브와 녹색 큐브는 **같은 의미**로 처리한다.
- 큐브 감지 시 컨베이어는 기본적으로 **시계방향 회전**으로 구동하되, `run_counter_clockwise`도 명령값으로 지원한다.
- 수동 긴급정지를 위해 `emergency_stop` 명령값을 추가한다.
- 큐브가 ROI 안에서 **10프레임 연속 미검출**되면 이송 완료로 보고 컨베이어를 멈춘다.
- D435i는 ROS 2 `realsense2_camera` topic으로 통신한다.
- 컨베이어 모터는 Raspberry Pi에서 **Modbus TCP**로 제어한다.
- Python Modbus 라이브러리는 **`pymodbus==3.13.1`**로 고정한다.
- Modbus는 추후 모든 로봇 동작 상태와 농장 현황을 관리하는 공통 상태/제어 레이어로 확장한다.

## 2. 가능성 판단

가능하다. 오히려 현재 단계에서는 `entry/middle/exit` ROI를 나누는 것보다 **단일 ROI + 색상 큐브 감지 + 사라짐 판단**이 더 안정적이고 구현이 빠르다.

장점:
- 빨간색/녹색 큐브는 색상 threshold로 검출하기 쉽다.
- 컨베이어 방향을 정확히 몰라도 동작 가능하다.
- 복잡한 tracking 없이 `있음 -> 없음` 상태 전이만 보면 된다.
- Modbus 제어도 `cube_detected=true면 run`, `cube_lost_stable=true면 stop`처럼 단순해진다.

주의할 점:
- 큐브가 순간적으로 가려지거나 조명 때문에 threshold가 깨질 수 있으므로 바로 멈추지 말고 `N프레임 연속 미검출` 또는 `0.5~1.0초 미검출` 조건을 둔다.
- 빨강/초록 HSV 범위는 실제 조명에서 캘리브레이션해야 한다.
- ROI 밖의 빨간/초록 물체가 보이면 오검출될 수 있으므로 컨베이어 ROI를 벨트 영역에 최대한 타이트하게 잡는다.

## 3. 샘플 이미지 기준 관찰

이미지 크기: `1280x720` 기준으로 보이며, 컨베이어는 화면 **왼쪽 영역**에 있다.

시각적 판단:
- 컨베이어 전체 조립체 후보 영역: 대략 `x=70~430`, `y=20~360`
- 실제 검은 벨트 후보 영역: 대략 `x=140~370`, `y=35~335`
- 감지는 전체 화면이 아니라 top-view로 보정한 프레임의 벨트 ROI 안에서만 수행한다.
- 프레임이 비스듬하게 찍히므로 **원본 프레임에서 컨베이어 평면 4점을 클릭해 top-view로 보정한 뒤**, 보정된 top-view 프레임에서 `conveyor_roi` 4점을 다시 지정한다.

## 4. 목표 아키텍처

```text
D435i / RealSense
  └─ ROS 2 realsense2_camera
      └─ /camera/.../color/image_raw
          └─ conveyor_vision_node
              1. raw frame 수신
              2. raw frame에서 topview source quad 적용
              3. perspective transform으로 top-view frame 생성
              4. top-view 기준 conveyor_roi crop
              5. HSV 기반 red/green cube mask 생성
              6. contour 면적/중심점 계산
              7. cube_detected / cube_color / disappeared 판단
              8. /conveyor/vision/event publish
              9. annotated frame 저장/웹 표시용 전달

Raspberry Pi
  └─ Modbus 기반 컨베이어 모터 제어
      ├─ cube_detected 또는 run command 수신 시 motor run
      ├─ cube_disappeared stable 상태에서 motor stop
      ├─ conveyor status register 관리
      └─ 추후 robot/farm status register 확장

Backend/Web
  ├─ 컨베이어 이벤트 저장
  ├─ 현재 컨베이어 상태 표시
  └─ ROI annotated frame 표시
```

## 5. 좌표/ROI 초안

샘플 이미지 기준 임시값이다. 실제 ROI 캘리브레이션 후 갱신한다.

```yaml
image_size: [1280, 720]
perspective_transform_enabled: true
topview:
  # 원본 프레임 기준. scripts/select_conveyor_roi.py에서 4점 클릭으로 저장
  source_quad_raw_xy_tl_tr_br_bl: []
  size_wh: []
  output_size_mode: raw
  point_order_mode: click
  source_padding_ratio: 0.0
conveyor_roi:
  # top-view 프레임 기준. scripts/select_conveyor_roi.py에서 4점 클릭으로 저장
  coordinate_space: topview
  quad_xy_tl_tr_br_bl: []
  xyxy: []
# 감지 대상 색상
cube_colors: [red, green]
# N프레임 연속 미검출 시 delivered/stop 처리
disappear_stable_frames: 10
min_cube_area_px: 300
motor_direction: clockwise
modbus:
  mode: tcp
  library: pymodbus==3.13.1
```

## 6. 상태 머신 초안

```text
IDLE
  - ROI 안에 red/green cube 감지
  - red/green은 같은 의미로 처리
  - event: cube_detected
  - modbus_command: run_clockwise 또는 run_counter_clockwise
  -> RUNNING

RUNNING
  - cube가 계속 보이면 motor run 유지
  - cube가 잠깐 안 보여도 disappear_stable_frames 전까지는 run 유지
  - N프레임 연속 미검출
  - event: cube_disappeared / delivered
  - modbus_command: stop
  -> DELIVERED

DELIVERED
  - stop 명령 확인 후 IDLE 복귀
```

## 7. 이벤트 포맷 초안

```json
{
  "timestamp": "ISO-8601",
  "camera_id": "camera2_d435i",
  "frame_id": "camera_color_optical_frame",
  "source_topic": "/camera/camera/color/image_raw",
  "roi_name": "conveyor_roi",
  "cube_detected": true,
  "cube_color": "red | green | unknown | none",
  "event_type": "cube_detected | cube_visible | cube_disappeared | delivered | missing | error",
  "transport_status": "idle | running | delivered | abnormal",
  "bbox_xyxy": [0, 0, 0, 0],
  "center_xy": [0, 0],
  "area_px": 0,
  "depth_mm": null,
  "modbus_command": "run | stop | none",
  "decision_source": "camera2_conveyor_single_roi_color"
}
```

## 8. 파일 구조 계획

```text
workspaces/지웅/conveyor/
  README.md
  requirements.txt
  .gitignore
  config/
    conveyor_roi_topview.json
    modbus_register_map.yaml
  config/previews/
    conveyor_roi_topview_raw_topview_quad.png
    conveyor_roi_topview_topview.png
    conveyor_roi_topview_topview_roi.png
  scripts/
    select_conveyor_roi.py
    color_cube_detector.py
  conveyor_vision/
    __init__.py
    event_schema.py
    conveyor_state_machine.py
    ros_conveyor_vision_node.py
    modbus_conveyor_client.py
  tests/
    test_color_cube_detector.py
    test_conveyor_state_machine.py
    test_event_schema.py
  output/
    annotated_realsense_test_image.png
```

## 9. 단계별 작업 계획

### Phase 1 — 상단뷰 + 컨베이어 ROI 좌표 세팅 도구
1. 작업환경은 `/home/ssafy/work/SmartFarmProject/workspaces/지웅/conveyor`로 관리한다.
2. `scripts/select_conveyor_roi.py` 작성
   - **권장 입력: 실제 RealSense ROS color topic** `--ros-topic /camera/camera/color/image_raw`
   - ROS preview 창에서 `SPACE`로 현재 프레임을 고정한 뒤 좌표 세팅 진행
   - top-view 출력은 기본적으로 원본 ROS 프레임 크기와 같은 `--topview-size-mode raw`를 사용한다. 클릭한 quad 크기만큼 작은 프레임으로 뜨는 문제를 피하기 위함이다.
   - 스크린샷 기준 추가 문제인 “지정한 4점보다 안쪽 영역이 top-view로 잡히는 것처럼 보이는 현상”을 줄이기 위해 기본 point order는 자동 정렬이 아니라 클릭 순서(`--point-order click`)를 사용한다.
   - 좌표 창은 `WINDOW_AUTOSIZE`로 띄워 OpenCV 창 리사이즈에 따른 마우스 좌표 오차를 줄인다. 화면에 크면 창을 줄이지 말고 `--display-scale`을 사용한다.
   - 여전히 경계가 조금 잘려 보이면 `--source-padding-ratio 0.02~0.03`으로 source quad를 살짝 확장한다.
   - 보조 입력: `references/realsense-test-image.png`, `--camera 0`, `--video <path>`
   - `마우스이벤트1`: 원본 프레임에서 상단뷰 변환용 4점 클릭
   - perspective transform으로 top-view 프레임 생성 및 표시
   - `마우스이벤트2`: top-view 프레임에서 컨베이어 ROI 4점 클릭
   - 출력: `config/conveyor_roi_topview.json`
   - 확인용 preview: 원본 quad, top-view, top-view ROI 이미지 저장
3. JSON의 `source.source_type=ros_topic`, `source.topic`, `source.encoding`, `raw_frame.width/height`, `topview.source_quad_raw_xy_tl_tr_br_bl`, `topview.perspective_matrix_raw_to_topview`, `conveyor_roi.quad_xy_tl_tr_br_bl`, `conveyor_roi.xyxy`를 이후 감지 코드에서 사용한다.
4. 빨강/초록 큐브가 있는 테스트 이미지가 생기면 top-view ROI 안에서 색상 검출 결과를 시각화한다.

### Phase 2 — 빨강/초록 큐브 감지
1. `color_cube_detector.py` 작성
2. HSV 색상 범위로 red/green mask 생성
3. contour 면적 필터링
4. 가장 큰 큐브 후보의 `bbox`, `center`, `area`, `color` 반환
5. ROI 안에 큐브가 없으면 `cube_detected=false` 반환

### Phase 3 — 컨베이어 상태 머신
1. `conveyor_state_machine.py` 작성
2. `IDLE -> RUNNING -> DELIVERED -> IDLE` 상태 전이 구현
3. `disappear_stable_frames`로 순간 미검출에 의한 오정지 방지
4. 상태별 `modbus_command` 생성
   - cube detected: `run_clockwise` 또는 `run_counter_clockwise`
   - cube disappeared stable: `stop`
   - manual emergency: `emergency_stop`

### Phase 4 — RealSense ROS 연동
1. `ros2 launch realsense2_camera rs_launch.py` 실행 후 topic 확인
   ```bash
   ros2 topic list | grep -E 'color|depth|camera'
   ```
2. color image topic 후보 확인
   - 예: `/camera/camera/color/image_raw`
3. `ros_conveyor_vision_node.py` 작성
   - subscribe: RealSense color image
   - process: top-view 변환 + top-view ROI crop + red/green cube detect + state machine
   - publish: `/conveyor/vision/event`
   - save/publish: annotated frame

### Phase 5 — Raspberry Pi + Modbus TCP 모터 제어 연동
1. Python 의존성은 `pymodbus==3.13.1`로 고정
2. Raspberry Pi에서 Modbus TCP 클라이언트/서버 역할과 모터 드라이버 접속 IP/port 확인
3. `modbus_register_map.yaml` 작성
   - red/green은 같은 `cube_detected` 의미로 기록
   - `run_clockwise`, `run_counter_clockwise`, `stop`, `reset`, `emergency_stop` 명령을 분리
4. `conveyor_modbus.py` / `conveyor_modbus_command.py` 작성
   - `run_clockwise` command -> 컨베이어 모터 시계방향 ON
   - `run_counter_clockwise` command -> 컨베이어 모터 반시계방향 ON
   - `stop` command -> 컨베이어 모터 OFF
   - `emergency_stop` command -> 즉시 정지용 긴급 명령
5. 실제 모터 없이 `modbus_dry_run`과 fake client 단위 테스트로 먼저 검증
6. Raspberry Pi/모터 드라이버 연결 후 실기기 검증

### Phase 6 — 웹 표시 연동
1. 웹에 보여줄 데이터 분리
   - 원본 프레임
   - ROI annotated frame
   - cube color/status
   - conveyor motor status
2. 우선 ROI annotated frame + 이벤트 JSON을 표시한다.
3. Django/DB에는 이벤트 JSON 저장
4. 대시보드에는 현재 상태와 최근 이벤트 표시

## 10. Modbus register map 확정안

Modbus TCP server는 `192.168.110.109:50200`이다. 비전 노드는 TCP client로 아래 holding register block을 쓴다.

```yaml
holding_registers:
  conveyor:
    40021: conveyor_command      # 0 stop, 1 run_clockwise, 2 run_counter_clockwise, 3 reset, 4 emergency_stop
    40022: conveyor_speed_cmd    # rpm 또는 percent
    40023: conveyor_status       # 0 idle, 1 running, 2 delivered, 3 error, 4 emergency_stopped
    40024: conveyor_error_code   # 0 none, 1 modbus_write_failed, 2 invalid_command
    40025: cube_detected         # 0 false, 1 true
    40026: cube_color            # 0 none, 1 red, 2 green, 3 unknown
    40027: last_vision_event     # 0 none, 1 cube_detected, 2 cube_lost, 3 delivered, 4 error, 5 emergency_stop
    40028: reserved_conveyor_1
    40029: reserved_conveyor_2
    40030: reserved_conveyor_3
  robots:
    40100: dobot_status
    40110: turtlebot_status
  farm:
    40200: temperature_x10
    40201: humidity_x10
    40202: soil_moisture_x10
coils:
  00001: conveyor_run
  00002: conveyor_reset
  00010: alarm_enable
```

주소 기준:
- pymodbus는 기본적으로 40021을 protocol address `20`으로 쓴다.
- 이 구현도 기본값은 `modbus_zero_based_addresses:=true`이다.
- 서버가 literal `40021` 주소를 요구하면 `modbus_zero_based_addresses:=false`로 바꾼다.

## 11. 남은 확인 항목

아래는 구현 직전 또는 실기기 연결 시 확정하면 된다.

1. 실제 서버가 40021을 protocol address `20`으로 받는지, literal `40021`로 받는지
2. 큐브가 ROI에서 10프레임 연속 사라진 뒤 **즉시 정지**할지, 정지 명령 전/후에 아주 짧은 추가 구동 시간이 필요한지
3. 웹에는 원본 이미지, ROI annotated 이미지, 이벤트 상태 중 무엇을 우선 띄울지

## 12. 1차 완료 기준

- `scripts/select_conveyor_roi.py --ros-topic /camera/camera/color/image_raw`로 실제 ROS frame을 고정하고, 원본 4점 → top-view 변환 → top-view ROI 4점 지정 결과가 `config/conveyor_roi_topview.json`에 저장됨
- preview 이미지로 원본 quad, top-view, top-view ROI 결과를 확인할 수 있음
- 빨강/초록 큐브가 있는 이미지에서 `cube_detected`, `cube_color`, `bbox`, `center`가 생성됨
- 큐브 감지 시 `run_clockwise` 또는 `run_counter_clockwise`, 큐브 N프레임 연속 미검출 시 `stop`, 수동 필요 시 `emergency_stop` command가 생성됨
- ROS topic 입력으로 같은 로직이 동작함
- Modbus register map 초안이 문서화됨
- 웹 표시용 ROI annotated frame 산출 경로가 정리됨

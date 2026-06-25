# SmartFarmProject Conveyor 작업 메모

작성일: 2026-06-24
범위: 이 문서는 이 쓰레드에서 집중 관리할 **컨베이어 + D435i + OpenCV + ROI 기반 흐름 확인 파트**의 실행 메모다.

## 1. 현재 문서 검토 기준
검토한 문서:
- `README.md`
- `docs/진행_로그.md`
- `docs/작업_결정_메모.md`
- `docs/R&R_초안.md`
- `docs/WBS_검토_메모.md`
- `docs/WBS_재검토_메모.md`
- `docs/Vision_작업_메모.md`
- `docs/시스템_데이터_흐름_초안.md`
- `workspaces/지웅/vision/README.md`
- `references/WBS.xlsx`

## 2. 이 쓰레드의 집중 범위
이 쓰레드에서는 **컨베이어 위 2번 카메라 기반 흐름 확인**만 집중해서 정리한다.

### 직접 다룰 것
- 컨베이어 상단 D435i 카메라 배치/시야 기준
- OpenCV 프레임 수집 및 ROI 설정
- 벨트 영역/진입/중앙/출구 구간 ROI 분리
- 작물 존재 여부, 위치, 이동 상태, 이탈/누락 감지
- 컨베이어 구동/정지 판단에 필요한 이벤트 포맷
- 서버/ROS로 넘길 컨베이어 상태 로그 포맷

### 인터페이스 수준에서만 언급할 것
- 1번 카메라의 작물 종류/정상·불량 판정
- Dobot 좌표/수확/촬영/컨베이어 적재 시퀀스
- 웹 대시보드 화면 구현 상세
- TurtleBot SLAM/배송 구현

## 3. 현재 확정된 컨베이어 역할
- 1번 카메라 결과가 최종 판정의 권위 소스다.
- 정상 판정된 작물만 Dobot이 컨베이어 시작점에 올린다.
- 컨베이어 파트는 작물 종류/불량 여부를 다시 판정하지 않는다.
- 2번 카메라(D435i)는 컨베이어 위 작물의 `존재`, `위치`, `타이밍`, `흐름 이상`을 확인한다.
- 정상 작물은 컨베이어 끝의 공용 수거 상자로 낙하한다.

## 4. D435i + OpenCV + ROI 기준 1차 구현 방향
### 4.1 MVP 기본 전략
- MVP에서는 **RGB 프레임 + 고정 ROI** 기반 감지를 먼저 구현한다.
- D435i의 depth는 초기 MVP 필수 조건으로 묶지 않고, RGB ROI 감지가 불안정할 때 보조 검증 정보로 추가한다.
- 카메라는 컨베이어 정중앙 상단에서 아래를 보도록 두고, 벨트가 프레임 안에서 최대한 직사각형에 가깝게 보이도록 고정한다.

### 4.2 ROI 구간 초안
고정 ROI를 아래처럼 나눠 시작한다.

| ROI | 목적 | 대표 이벤트 |
|---|---|---|
| `belt_roi` | 벨트 전체 감시 영역 | `object_detected`, `misaligned` |
| `entry_roi` | Dobot이 올린 작물 진입 확인 | `entered` |
| `middle_roi` | 정상 이동 중인지 확인 | `moving` |
| `exit_roi` | 끝 도달/낙하 직전 확인 | `exited`, `delivered` |

초기 구현에서는 좌표를 코드 상수 또는 JSON/YAML 설정으로 두고, 실제 카메라 화면을 보며 ROI를 보정한다.

### 4.3 감지 로직 초안
1. D435i RGB 프레임을 OpenCV로 읽는다.
2. `belt_roi`만 잘라서 배경/벨트 영역을 기준으로 전처리한다.
3. 색/명도 차이, 배경 차분, contour 면적 등 단순한 OpenCV 방법으로 작물 후보를 찾는다.
4. 후보 중심점이 `entry_roi -> middle_roi -> exit_roi` 순서로 이동하는지 추적한다.
5. 일정 시간 안에 다음 ROI로 넘어가지 않으면 `missing`, `stalled`, `misaligned` 같은 예외 이벤트를 낸다.
6. `exit_roi` 통과가 확인되면 `transport_status=delivered`로 기록한다.

## 5. 컨베이어 이벤트 포맷 초안
```json
{
  "inspection_id": "string",
  "timestamp": "ISO-8601",
  "camera_id": "camera2_d435i",
  "object_detected": true,
  "roi_name": "entry_roi | middle_roi | exit_roi | belt_roi",
  "belt_position": "entry | middle | exit | unknown",
  "event_type": "entered | moving | exited | missing | stalled | misaligned",
  "transport_status": "in_progress | delivered | abnormal",
  "bbox_xyxy": [0, 0, 0, 0],
  "center_xy": [0, 0],
  "depth_mm": null,
  "decision_source": "camera2_conveyor_roi"
}
```

## 6. WBS/R&R 연결
### WBS 연결 항목
- `HW 세팅(1)`: Dobot, TurtleBot, 컨베이어벨트 기본 조립
- `HW 세팅(2)`: 라즈베리파이 연동, RGB-D 카메라 구성
- `비전 제어`: OpenCV 프레임 전처리 및 실시간 추론/감지 파이프라인
- `장치 제어`: RGB-D 객체 인식 기반 컨베이어 구동/정지 및 적재 로직
- `시스템 연동`: 컨베이어 상태/이벤트를 서버 로그로 전달

### R&R 연결
- Participant1: D435i/OpenCV/ROI 감지 파이프라인과 카메라 입출력 명세
- Participant2: Dobot이 컨베이어 시작점에 정상 작물을 올리는 위치/타이밍 인터페이스
- Participant3: 컨베이어 이벤트 저장/API/대시보드 표시 포맷

## 7. 바로 다음 액션
1. D435i가 연결된 PC/라즈베리파이 실행 위치를 확정한다.
2. 실제 D435i RGB 프레임 1장을 저장하고, 컨베이어가 보이는 영역에 `belt_roi`, `entry_roi`, `middle_roi`, `exit_roi`를 그려 좌표를 정한다.
3. 저장 이미지/동영상 기준으로 OpenCV contour 기반 감지 스크립트를 먼저 만든다.
4. 실시간 카메라 입력으로 전환한 뒤, ROI별 이벤트 로그가 순서대로 나오는지 확인한다.
5. 컨베이어 모터 제어는 감지 로그가 안정화된 뒤 `object_detected`/`delivered` 이벤트에 연결한다.

## 8. 2026-06-24 D435i / RealSense ROS 실행 진단
사용자가 D435i를 연결한 뒤 아래 명령에서 오류가 난다고 보고했다.

```bash
ros2 launch realsense2_camera rs_launch.py
```

현재 PC에서 확인한 결과:
- USB 장치 인식: 정상
  - `lsusb` 결과: `8086:0b3a Intel(R) RealSense(TM) Depth Camera 435i`
- ROS 2 Humble 설치: `/opt/ros/humble/setup.bash` 존재
- `realsense2_camera` ROS 패키지: 미설치
  - 재현 오류: `Package 'realsense2_camera' not found: "package 'realsense2_camera' not found, searching: ['/opt/ros/humble']"`
- `librealsense2-utils`, `librealsense2-dev`: 미설치
- apt 후보 패키지는 존재:
  - `ros-humble-realsense2-camera`
  - `ros-humble-realsense2-camera-msgs`
  - `librealsense2-utils`
  - `librealsense2-udev-rules`

판단:
- 현재 오류의 1차 원인은 D435i 하드웨어 연결 문제가 아니라 **ROS RealSense wrapper 패키지 미설치**다.
- SDK/유틸리티도 설치되어 있지 않으므로, `rs-enumerate-devices`로 장치 상세 확인을 하려면 `librealsense2-utils`도 설치해야 한다.

권장 설치/검증 순서:

```bash
sudo apt update
sudo apt install -y \
  ros-humble-realsense2-camera \
  ros-humble-realsense2-camera-msgs \
  librealsense2-utils \
  librealsense2-udev-rules

source /opt/ros/humble/setup.bash
ros2 pkg list | grep realsense2_camera
rs-enumerate-devices
ros2 launch realsense2_camera rs_launch.py
```

만약 설치 후에도 장치 권한 문제가 나면 USB를 뽑았다 다시 꽂거나, udev rule 적용을 위해 재부팅한다.

## 9. 2026-06-24 샘플 이미지 기반 단일 ROI/Modbus 계획
샘플 이미지:
- `references/realsense-test-image.png`

확정/전제:
- D435i는 **ROS 2 RealSense wrapper**로 통신한다.
- 감지 대상은 작물이 아니라 **컨베이어 위 빨간색/녹색 큐브**다.
- ROI를 `entry/middle/exit`로 나누지 않고, top-view로 보정된 컨베이어/벨트 영역을 **단일 `conveyor_roi`**로 잡는다.
- 좌표 세팅은 실제 detector와 같은 ROS color topic frame을 직접 받아 수행한다. 권장 실행은 `scripts/select_conveyor_roi.py --ros-topic /camera/camera/color/image_raw`이다.
- 원본 ROS 프레임에서 컨베이어 평면 4점을 클릭해 top-view로 보정한 뒤, top-view 프레임에서 ROI 4점을 클릭해 좌표를 저장한다.
- `conveyor_roi` 안에서 빨간색/녹색 큐브가 감지되면 컨베이어를 움직이고, 큐브가 ROI에서 10프레임 연속 미검출되면 이송 완료로 보고 멈춘다.
- 좌표 세팅 도구는 `/home/ssafy/work/SmartFarmProject/workspaces/지웅/conveyor/scripts/select_conveyor_roi.py`에 두고, 결과는 `config/conveyor_roi_topview.json`으로 저장한다.
- 웹에는 추후 원본/ROI annotated 화면 또는 이벤트 상태를 표시할 예정이다.
- 빨강/초록이 같은 의미이며, 큐브 감지 시 컨베이어는 시계방향으로 구동한다.
- `disappear_stable_frames`는 **10프레임**으로 확정한다.
- 컨베이어 모터는 Raspberry Pi에서 동작시키고, 모터 제어는 **Modbus TCP + `pymodbus==3.13.1`**를 사용한다.
- Modbus는 추후 컨베이어뿐 아니라 모든 로봇의 동작 상태, 농장 현황 등 다양한 상태 정보를 관리하는 공통 상태/제어 레이어로 확장한다.

샘플 이미지 관찰:
- 컨베이어는 이미지 왼쪽에 있다.
- 전체 프레임에는 Dobot, 격자판, 버튼 박스, 케이블 등이 같이 들어와 있어 전체 화면 감지는 오검출 위험이 크다.
- 따라서 전체 프레임이 아니라 단일 `conveyor_roi` 안에서만 빨강/초록 HSV 색상 감지를 수행한다.

초기 좌표 후보:
- 컨베이어 전체 조립체 후보: `x=70~430`, `y=20~360`
- 감지용 검은 벨트/컨베이어 ROI 후보: `x=140~370`, `y=35~335`
- config 초안: `config/conveyor_roi_topview.json`에 ROS topic/source metadata, 원본 ROS frame 해상도, 원본 4점, top-view 크기/행렬, `topview.output_size_mode: raw`, `topview.point_order_mode: click`, `topview.source_padding_ratio`, top-view 기준 `conveyor_roi` 4점/`xyxy`, `disappear_stable_frames: 10`, `min_cube_area_px: 300` 저장

구현 계획 문서:
- `docs/Conveyor_ROI_Modbus_구현_계획.md`

## 10. 2026-06-24 ROS2 top-view ROI 색상 감지 테스트 노드
사용자가 실제 좌표 세팅을 마친 뒤, 빠르게 실시간 확인할 수 있는 ROS2 테스트 패키지를 추가했다.

패키지/노드:
- workspace: `/home/ssafy/work/SmartFarmProject/workspaces/지웅/ros2_ws`
- package: `conveyor_vision_test`
- entrypoint: `topview_color_detector`
- main file: `src/conveyor_vision_test/conveyor_vision_test/topview_color_detector.py`
- package README: `src/conveyor_vision_test/README.md`

동작:
1. `/camera/camera/color/image_raw`의 `sensor_msgs/Image`를 받는다.
2. `/home/ssafy/work/SmartFarmProject/workspaces/지웅/conveyor/config/conveyor_roi_topview.json`의 perspective matrix로 top-view를 만든다.
3. top-view 창에 `conveyor_roi`를 노란색 영역/외곽선으로 표시한다.
4. ROI 내부에서 HSV 기준 빨간색/초록색 blob을 찾고 bounding box를 표시한다.
5. annotated 이미지를 `/conveyor/topview_annotated`로 publish한다.
6. live frame 해상도와 calibration JSON 해상도가 다르면 기본적으로 처리를 중단해 잘못된 좌표 사용을 막는다.

실행:
```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select conveyor_vision_test
source install/setup.bash
ros2 run conveyor_vision_test topview_color_detector
```

창 크기를 줄여 보고 싶으면:
```bash
ros2 run conveyor_vision_test topview_color_detector --ros-args \
  -p display_scale:=0.7
```

GUI 없이 publish만 확인하려면:
```bash
ros2 run conveyor_vision_test topview_color_detector --ros-args \
  -p show_windows:=false
```

검증 결과:
- `/usr/bin/python3 -m py_compile` 통과
- 단위 테스트 `2 passed`
- `colcon build --packages-select conveyor_vision_test` 통과
- `colcon test --packages-select conveyor_vision_test` 결과 `2 tests, 0 errors, 0 failures`
- `ros2 run ... -p show_windows:=false` smoke 실행에서 config 로드, topic subscribe, top-view size `(1280, 720)` 확인

## 11. 2026-06-24 Modbus TCP 연동 반영
컨베이어 비전 노드에 Modbus TCP client 쓰기 로직을 붙였다.

서버/의존성:
- Modbus TCP server: `192.168.110.109:50200`
- 기존 Python dependency: `pymodbus==3.9.2`
- 기존 환경 설치 확인: `/usr/bin/python3 -m pip install --user pymodbus==3.9.2`, import 확인 완료
- 이후 13절 계획에서 `pymodbus==3.13.1` async 구조로 전환 결정

Holding register map:
| Register | Name | 값 |
|---:|---|---|
| 40021 | `conveyor_command` | `0 stop`, `1 run_clockwise`, `2 run_counter_clockwise`, `3 reset`, `4 emergency_stop` |
| 40022 | `conveyor_speed_cmd` | 속도 명령값 |
| 40023 | `conveyor_status` | `0 idle`, `1 running`, `2 delivered`, `3 error`, `4 emergency_stopped` |
| 40024 | `conveyor_error_code` | `0 none`, `1 modbus_write_failed`, `2 invalid_command` |
| 40025 | `cube_detected` | `0 false`, `1 true` |
| 40026 | `cube_color` | `0 none`, `1 red`, `2 green`, `3 unknown` |
| 40027 | `last_vision_event` | `0 none`, `1 cube_detected`, `2 cube_lost`, `3 delivered`, `4 error`, `5 emergency_stop` |
| 40028~40030 | reserved | 컨베이어 확장 예비 |

주소 기준:
- pymodbus 기본 방식에 맞춰 40021은 protocol address `20`으로 변환한다.
- 서버가 literal 40021 주소를 요구하면 `-p modbus_zero_based_addresses:=false`로 바꾼다.

비전-제어 상태 흐름:
1. ROI 안에 빨강/초록 큐브 감지: Pi status가 허용 상태이면 `conveyor_command=run_clockwise` 또는 `run_counter_clockwise`, `cube_detected=1`, `cube_color=red/green`을 쓴다. `conveyor_status`는 Pi가 실제 모터 기준으로 갱신한다.
2. 일시 미검출: 구동 명령은 유지하고 `cube_detected=0`, `last_vision_event=cube_lost`를 쓴다.
3. `disappear_stable_frames=10`프레임 연속 미검출: `conveyor_command=stop`, `last_vision_event=delivered`를 쓴다. `conveyor_status=delivered`는 Pi controller가 모터 상태 기준으로 표현한다.

실행 예시:
```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select conveyor_vision_test
source install/setup.bash

ros2 run conveyor_vision_test topview_color_detector --ros-args \
  -p modbus_enabled:=true \
  -p modbus_host:=192.168.110.109 \
  -p modbus_port:=50200 \
  -p conveyor_run_command:=run_clockwise \
  -p conveyor_speed_cmd:=100
```

반시계 방향 테스트:
```bash
ros2 run conveyor_vision_test topview_color_detector --ros-args \
  -p modbus_enabled:=true \
  -p conveyor_run_command:=run_counter_clockwise
```

수동 긴급정지:
```bash
ros2 run conveyor_vision_test conveyor_modbus_command emergency_stop
```

검증 결과:
- `conveyor_modbus.py`, `conveyor_modbus_command.py` 추가
- `topview_color_detector.py`에 state machine + Modbus write 연동
- 단위 테스트가 2개에서 7개로 증가했고 `7 passed`
- `colcon build --packages-select conveyor_vision_test` 통과
- `colcon test --packages-select conveyor_vision_test` 결과 `7 tests, 0 errors, 0 failures`
- 실제 서버에는 쓰지 않고 `modbus_dry_run:=true` smoke 실행으로 register snapshot 로그를 확인했다.

## 12. 아직 결정할 것
- 실제 서버가 40021을 protocol address `20`으로 받는지, literal `40021`로 받는지 최종 확인
- 큐브가 ROI에서 사라진 뒤 바로 멈출지, 추가로 몇 초 더 구동할지
- 웹 우선 표시 대상: 원본 이미지 / ROI annotated 이미지 / 이벤트 상태
- depth 사용 범위: MVP에서 제외할지, 큐브 높이/벨트 배경 분리 보조로 쓸지


## 13. 2026-06-24 pymodbus 3.13.1 / Raspberry Pi 5 제어 구조 전환 계획

문제:
- 기존 `pymodbus==3.9.2` 동기식 client 구조에서 여러 Modbus client가 server에 read/write하면 ROS/OpenCV 처리와 제어가 버벅일 수 있다.
- 특히 image callback 내부에서 Modbus 네트워크 I/O를 기다리면 D435i frame 처리와 top-view 표시가 함께 지연될 수 있다.

전환 결정:
- Modbus 기준 버전은 **`pymodbus==3.13.1`**로 변경한다.
- Modbus TCP server는 `192.168.110.109:50200`의 외부/shared register layer로 둔다.
- Raspberry Pi 5/Raspbian은 **Modbus client + 컨베이어 모터 GPIO 제어**를 담당한다.
- PC/ROS2 비전 노드도 Modbus client이며, `AsyncModbusTcpClient` 기반 async writer를 사용하고 image callback에서는 최신 상태만 queue에 넣고 즉시 반환한다.
- server는 holding register `40021~40030`을 유지하되, 실제 pymodbus protocol address는 기본 `20~29`로 사용한다.

역할 분리:
- PC/D435i/OpenCV: top-view 변환, 단일 ROI HSV 큐브 감지, command/vision register write(`40021/40022/40025~40027`).
- Raspberry Pi 5: command register polling, `DIR/STEP/ENABLE` GPIO 제어, 실제 모터 상태 기준 status/error register write(`40023/40024`).
- Modbus server: shared holding register layer 유지.
- Dashboard/backend: MVP에서는 가능하면 read-only로 status/event 확인.

상세 계획:
- `docs/Conveyor_Modbus_Async_RaspberryPi_전환_계획.md`
- Obsidian: `[[Conveyor Modbus Async + Raspberry Pi 전환 계획]]`

## 14. 2026-06-24 Modbus server/Pi client 역할 정정

사용자 확인 사항:
- Modbus server는 `192.168.110.109:50200`이다.
- Raspberry Pi 5/Raspbian 접속 대상은 `ssafy@192.168.110.139`이다. 비밀번호는 보안상 문서에 저장하지 않는다.

정정된 구조:
- Raspberry Pi는 Modbus server가 아니라 **Modbus client**로 동작한다.
- PC/ROS2 D435i 비전 노드도 Modbus client다.
- 두 client 모두 외부 server `192.168.110.109:50200`의 conveyor register block `40021~40030`에 접근한다.
- PC vision client는 `40021/40022/40025/40026/40027` 중심으로 write한다.
- Raspberry Pi client는 `40021/40022`를 읽어 컨베이어 GPIO를 제어하고, 실제 모터 상태 기준으로 `40023/40024`를 write한다.
- 이 구조에서는 `pymodbus==3.13.1` async client를 쓰는 것이 더 중요하다. 여러 client의 read/write가 있어도 ROS image callback이나 Pi motor loop가 blocking되지 않게 해야 한다.

## 15. 2026-06-24 Raspberry Pi Modbus client + GPIO controller 계획

사용자 요청에 따라 라즈베리파이에 올릴 컨베이어 제어 클라이언트 계획을 세웠다.

확정/가정:
- Pi는 외부 Modbus server `192.168.110.109:50200`에 붙는 **Modbus client**다.
- Pi controller 한 프로그램 안에 `pymodbus==3.13.1` async client, GPIO motor control, button handling을 포함한다.
- GPIO는 기존 코드 기준 `DIR=17`, `STEP=27`, `ENABLE=22`, button `23/24`를 사용한다.
- 기존 버튼은 `GPIO23=긴급정지`, `GPIO24=재시작`으로 재정의한다.
- 긴급정지 버튼은 모터를 즉시 disable하고 `40023=emergency_stopped`, `40024=local_emergency_stop`을 write한다.
- 재시작 버튼은 emergency latch를 해제하고 idle/error none으로 상태를 되돌리되, 안전상 바로 모터를 재구동하지 않는다.
- 속도/가감속은 `ref/conveyor/conv_profile_지웅.py`의 `TargetSpeed=0.0001`, `InitialSpeed=0.0005`, `RATIO=0.0000005`를 기준으로 분리 구현한다.

상세 계획:
- `docs/Conveyor_Pi_Modbus_Client_Controller_구현_계획.md`
- Obsidian: `[[Conveyor Pi Modbus Client Controller 구현 계획]]`

## 16. 2026-06-24 Raspberry Pi controller 구현/배포 결과

구현 파일:
- `workspaces/지웅/conveyor/pi_controller/register_map.py`
- `workspaces/지웅/conveyor/pi_controller/motion_profile.py`
- `workspaces/지웅/conveyor/pi_controller/conveyor_motor.py`
- `workspaces/지웅/conveyor/pi_controller/conveyor_modbus_client_controller.py`
- `workspaces/지웅/conveyor/pi_controller/run_pi_controller.sh`
- `workspaces/지웅/conveyor/pi_controller/README.md`
- `workspaces/지웅/conveyor/pi_controller/tests/`

반영된 정책:
- Pi는 `40021` command register를 읽기만 한다.
- 긴급정지/재시작 버튼은 `40021`을 바꾸지 않고, `40023 status`, `40024 error_code`만 갱신한다.
- `GPIO23=긴급정지`, `GPIO24=재시작`.
- 재시작은 emergency latch 해제만 수행하고 즉시 재구동하지 않는다.

검증:
- 로컬 `py_compile` 통과
- 로컬 `pytest`: `13 passed`
- 로컬 `--dry-run-motor --dry-run-modbus` smoke 성공
- Raspberry Pi 배포 완료: `/home/ssafy/SmartFarmProject/workspaces/지웅/conveyor/pi_controller`
- Pi `.venv` 구성 완료, `pymodbus==3.13.1` 설치 확인, `gpiod import ok` 확인
- `run_pi_controller.sh` 실행 권한 설정 완료

현재 blocker:
- Pi에서 `192.168.110.109:50200` 접속 실패.
- Pi 기준 `ping 192.168.110.109` 100% packet loss, TCP check `No route to host`.
- Modbus server 장비/네트워크/라우팅을 확인한 뒤 실제 server dry-run을 재검증해야 한다.

## 17. 2026-06-24 RealSense ROS 비전 노드의 상태 기반 Modbus command gating

사용자 요청:
- RealSense ROS 코드에서 ROI 객체 탐지 시 Modbus로 컨베이어 command를 내린다.
- 단, Pi가 긴급정지 상태를 보고하고 있으면 command를 내리지 않는다.
- 그 외 상태별 처리 정책은 안전 우선으로 정한다.

구현 파일:
- `workspaces/지웅/ros2_ws/src/conveyor_vision_test/conveyor_vision_test/conveyor_modbus.py`
- `workspaces/지웅/ros2_ws/src/conveyor_vision_test/conveyor_vision_test/topview_color_detector.py`
- `workspaces/지웅/ros2_ws/src/conveyor_vision_test/test/test_topview_color_detector.py`
- `workspaces/지웅/ros2_ws/src/conveyor_vision_test/README.md`

Register ownership 반영:
- PC/ROS2 비전 노드는 `40021 command`, `40022 speed`, `40025 cube_detected`, `40026 cube_color`, `40027 last_vision_event`만 쓴다.
- Raspberry Pi controller는 실제 물리 상태 owner로서 `40023 conveyor_status`, `40024 conveyor_error_code`를 쓴다.
- 비전 노드는 command write 직전에 `40023/40024`를 읽어 상태를 확인한다.

상태별 command 정책:
| Pi status | 감지 결과 | PC/ROS command 처리 |
|---:|---|---|
| `0 idle` | cube detected | `run_clockwise` 또는 `run_counter_clockwise` + speed write |
| `1 running` | cube visible / transient lost | run 유지 |
| `1 running` | stable disappeared | `stop` write |
| `2 delivered` | 새 cube detected | run command 허용 |
| `3 error` | cube detected | run/reset 금지, vision register만 write |
| `3 error` | stable disappeared / stop desired | `stop`만 허용 |
| `4 emergency_stopped` | any | **40021/40022 command/speed write 금지**, 40025~40027 vision register만 write |
| status read 실패 | any | fail-safe: command 없이 vision register만 write |

검증:
```bash
source /opt/ros/humble/setup.bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/ros2_ws/src/conveyor_vision_test
/usr/bin/python3 -m pytest test/test_topview_color_detector.py -q
# 11 passed

cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/ros2_ws
/usr/bin/python3 -m py_compile \
  src/conveyor_vision_test/conveyor_vision_test/conveyor_modbus.py \
  src/conveyor_vision_test/conveyor_vision_test/topview_color_detector.py \
  src/conveyor_vision_test/conveyor_vision_test/conveyor_modbus_command.py
colcon build --packages-select conveyor_vision_test
colcon test --packages-select conveyor_vision_test --event-handlers console_direct+
colcon test-result --verbose
# Summary: 11 tests, 0 errors, 0 failures, 0 skipped
```

남은 실제 장비 검증:
- Modbus server `192.168.110.109:50200` 네트워크가 복구되면 `modbus_enabled:=true`로 실제 read/write smoke test.
- Pi local emergency button을 누른 상태에서 비전 노드가 `40021/40022`를 쓰지 않는지 server register log로 확인.

## 14. 2026-06-24 Modbus server 전용 범위 분리
- 이 쓰레드에서는 이후 **Modbus TCP server/shared register layer**만 집중한다.
- server endpoint는 `192.168.110.109:50200`이다.
- Raspberry Pi 5(`ssafy@192.168.110.139`)는 server가 아니라 client이며, 실제 GPIO motor controller와 `40023/40024` 상태 write를 담당한다.
- PC/ROS2 vision/manual client는 `40021/40022/40025~40027` 중심으로 write한다.
- 자세한 server 관점 register map, ownership, 네트워크 검증 순서는 `docs/Conveyor_Modbus_Server_작업_메모.md`에 분리했다.

## 18. 2026-06-24 컨베이어 미동작 1차 진단

증상:
- PC에서 RealSense `rs_launch.py`, Modbus server, `topview_color_detector` 실행.
- Raspberry Pi에서 `run_pi_controller.sh` 실행.
- Modbus server endpoint는 `192.168.110.109:50200`.
- 큐브 감지/Modbus 구동 조건으로 보이는데 실제 컨베이어가 움직이지 않음.

확인한 사실:
- server process cwd: `/home/ssafy/work/SmartFarmProject/workspaces/지웅/modbus`.
- server process는 `.venv`의 Python을 사용하며 `pymodbus==3.13.1`.
- ROS detector process는 `/usr/bin/python3`를 사용하며 이 환경의 `pymodbus`는 `3.9.2`.
- mock 검증에서 `pymodbus 3.13.1` server와 `pymodbus 3.9.2` client는 Modbus TCP protocol read/write가 정상 동작했다.
- register snapshot에서 `40021 command=1`, `40022 speed=100`, `40023 status=1`, `40025 detected=1`, `40026 color=2`, `40027 event=1`이 확인되었다. 이는 PC vision write와 Pi status write가 register layer까지는 도달했을 가능성이 높다는 뜻이다.

1차 판단:
- 단순히 PC와 server의 `pymodbus` Python 패키지 버전이 다르기 때문에 컨베이어가 안 도는 가능성은 낮다. Modbus TCP는 wire protocol이고, 실제 read/write가 확인되었다.
- 더 유력한 원인은 Raspberry Pi 실행 환경/옵션 또는 GPIO/motor layer다.

다음 확인 순서:
1. Pi에서 실제 실행 중인 Python이 `/home/ssafy/SmartFarmProject/workspaces/지웅/conveyor/pi_controller/.venv/bin/python`인지 확인.
2. Pi에서 `pymodbus.__version__ == 3.13.1`인지 확인.
3. `run_pi_controller.sh` 실행 시 `--dry-run-motor`가 붙어 있지 않은지 확인.
4. Pi log에서 `connected to Modbus server`, `wrote status=1 error=0`, `motor step loop started`가 나오는지 확인.
5. status가 running인데 모터가 안 움직이면 GPIO `DIR=17`, `STEP=27`, `ENABLE=22`, enable active-low, 모터 전원/드라이버 배선을 확인.

## 19. 2026-06-25 컨베이어 미동작 2차 진단 및 pymodbus 3.13.1 async 전환

추가 증상/로그:
```text
connected to Modbus server 192.168.110.109:50200
wrote status=0 error=0
motor step loop started direction=clockwise target_delay=0.0001000
wrote status=1 error=0
```

판단:
- `motor step loop started`가 이미 출력되었으므로, **Pi client가 command 변경을 수시로 확인하지 않아서 처음부터 모터가 안 돈다**는 설명은 현재 증상과 맞지 않는다.
- Pi runner는 `poll_interval_sec=0.05` 기본값으로 `40021/40022`를 반복 read한다.
- 다만 안전 보강으로 동일 run command가 유지되는 중 `motor.running == False`가 되면 같은 명령이라도 motor start를 재시도하도록 수정했다.
- 현재 가장 유력한 원인은 Modbus layer보다 아래의 GPIO/motor layer다: 잘못된 `gpiochip`, BCM pin mapping 차이, enable polarity, STEP/DIR/ENABLE 배선, 모터 드라이버 전원/ENA 상태, 드라이버가 받아들이기 어려운 pulse 조건.

코드 반영:
- Pi controller: `ConveyorController.apply_modbus_command()`가 같은 run command라도 실제 motor loop 상태가 stopped이면 재시작한다.
- Pi controller: GPIO setup 시 `chip/dir/step/enable/enable_active_low`를 log로 출력한다.
- ROS conveyor Modbus client: sync `ModbusTcpClient` 사용을 제거하고 `pymodbus.client.AsyncModbusTcpClient` + `device_id=` 기준의 pymodbus 3.13.1 async 방식으로 전환했다. ROS callback/CLI 호환을 위해 public sync wrapper는 유지하고 내부 Modbus I/O만 async로 수행한다.
- ROS package: `setup.py`와 `requirements.txt`에 `pymodbus==3.13.1`을 명시했다.
- PC `/usr/bin/python3.10` 환경의 `pymodbus`를 3.13.1로 업그레이드했다.

검증:
- Pi controller unit tests: `14 passed`.
- ROS conveyor vision tests: `12 passed`.
- ROS package build: `colcon build --packages-select conveyor_vision_test` 통과.
- PC ROS Python에서 `pymodbus.__version__ == 3.13.1` 확인.
- 임시 local Modbus server `127.0.0.1:55020`에서 manual command smoke: `run_clockwise --speed 77` write 후 `40021/40022 == [1, 77]` 확인.

다음 실제 장비 확인:
1. Pi에서 `gpioinfo | grep -E 'GPIO17|GPIO22|GPIO27|conveyor'`로 실제 line consumer가 잡히는지 확인.
2. Pi 5에서 `gpiochip0`로 안 움직이면 `./run_pi_controller.sh --gpio-chip gpiochip4`를 한 번 시도한다.
3. 기존 reference `../ref/conveyor/conveyor_test.py` 또는 같은 STEP/DIR/ENABLE 직접 pulse 테스트도 안 움직이면 코드/Modbus가 아니라 배선·전원·드라이버·enable polarity 문제로 본다.
4. 직접 pulse 테스트는 움직이고 `run_pi_controller.sh`만 안 움직이면 `gpiochip`, pin 번호, enable polarity, pulse timing을 controller 코드에서 장비값에 맞춰 조정한다.

## 20. 2026-06-25 Pi gpiod 누락 대응
- Pi에서 clean 재설치/테스트 중 `gpiod` Python binding이 없으면 `sudo apt install -y gpiod python3-libgpiod`를 먼저 설치한다.
- 이 controller는 libgpiod v1 API(`Chip.get_line`, `LINE_REQ_DIR_OUT`)를 사용하므로, venv는 `python3 -m venv --system-site-packages .venv`로 다시 만드는 것을 기본 절차로 정했다.
- `run_pi_controller.sh`에 real GPIO 실행 전 `gpiod` import와 `Chip.get_line` API 존재 여부를 검사하는 preflight를 추가했다. `--dry-run-motor`는 GPIO가 없어도 실행할 수 있게 preflight를 건너뛴다.

## 21. 2026-06-25 GPIO line 점유 상태와 직접 pulse 진단
- 사용자가 `gpioinfo | grep -E 'GPIO17|GPIO22|GPIO27|conveyor'` 결과를 공유했다. `GPIO17/22/27`이 `conveyor_dir/enable/step` consumer로 `[used]` 상태였으므로 Python `gpiod` import와 line request 자체는 성공한 상태로 판단한다.
- grep 결과가 두 번 반복되는 것은 `gpioinfo`의 chip header가 grep에서 제거되어 여러 gpiochip의 같은 이름 line이 섞여 보였을 가능성이 있다. 이후에는 `gpioinfo gpiochip0`와 `gpioinfo gpiochip4`를 분리해서 확인한다.
- line이 `[used]`인 동안은 기존 controller process가 GPIO를 잡고 있을 수 있으므로, 새 테스트 전 `pkill -f conveyor_modbus_client_controller.py`로 정리한다.
- Modbus/controller를 완전히 우회하는 `gpio_pulse_diagnostic.py`를 추가했다. 기본 chip, 반대 enable polarity, gpiochip4를 각각 직접 pulse하여 GPIO software 문제와 motor driver/배선/전원 문제를 분리한다.

## 22. 2026-06-25 직접 pulse 4조합 실패 판정
- 사용자가 `gpiochip0/gpiochip4`와 enable active-low/active-high 4개 직접 pulse 조합을 모두 시도했지만 모터가 움직이지 않았다고 보고했다.
- 이 결과는 Modbus/ROS/Pi controller 로직 원인 가능성을 매우 낮추고, 다음 원인 후보를 하드웨어 입력 계층으로 좁힌다: 드라이버 전원, ENA/PUL/DIR 배선, 공통 GND, Pi 3.3V 신호가 드라이버 optocoupler 입력 임계값을 넘지 못하는 문제, 모터 코일쌍/드라이버 DIP/current 설정.
- 다음 진단을 위해 `gpio_level_diagnostic.py`를 추가했다. STEP/DIR/ENABLE을 0.5초 주기로 느리게 토글해서 멀티미터/LED/로직프로브로 Pi pin과 드라이버 단자에서 실제 전압 변화가 도달하는지 확인한다.
- 판정 기준: Pi pin에서는 토글되지만 드라이버 단자에서 안 보이면 배선 문제, 드라이버 단자에서도 3.3V 토글은 보이나 모터가 안 움직이면 드라이버 입력 방식/전원/ENA/모터 결선 문제로 본다.

## 23. 2026-06-25 실드 사용 확인 후 공통 actuator 계층으로 재분류
- 사용자가 별도 모터 드라이버 배선이 아니라 이미 배선이 완성된 실드를 사용 중이며, 버튼 입력은 정상 작동하지만 스텝모터와 서보모터가 둘 다 작동하지 않는다고 보고했다.
- 버튼이 정상이라는 사실은 `gpiochip`, Python `gpiod`, button pin 23/24, 기본 입력 경로가 살아 있다는 증거다. 반대로 서로 다른 actuator인 stepper(GPIO17/27/22)와 servo(GPIO18)가 동시에 실패하므로 원인은 개별 스텝 드라이버보다 실드의 actuator 공통 계층으로 본다.
- 우선순위 후보: 실드 actuator 전원(VMOT/VIN/servo 5~6V rail) 미공급 또는 점퍼/스위치 OFF, 실드 OE/STBY/SLEEP/RESET enable 미처리, 실드가 raw GPIO가 아니라 I2C/PCA9685/TB6612 등 전용 인터페이스를 요구함, 실드 실제 pin mapping이 기존 reference의 `SERVO=18`, `DIR=17`, `STEP=27`, `ENABLE=22`와 다름.
- `shield_actuator_diagnostic.py`를 추가했다. 버튼 read, servo 50Hz hold, stepper pulse를 한 스크립트에서 실행해 "입력 GPIO는 정상인데 actuator 출력만 실패" 상태를 재현/기록한다.

## 24. 2026-06-25 Raspberry Pi OS 가능성 판정
- 사용자가 Pi OS 정보를 공유했다: `Linux raspberrypi 6.12.75+rpt-rpi-2712`, Debian GNU/Linux bookworm, `aarch64`.
- 현재 증거상 OS 자체가 1차 원인일 가능성은 낮다. 버튼이 정상 동작하고, 앞서 `gpiod` import/line request 및 `gpioinfo` consumer 표시가 확인되었기 때문에 kernel/libgpiod/GPIO 입력 경로는 살아 있다고 본다.
- 단, OS/라이브러리 계층이 완전히 무관한 것은 아니다. Raspberry Pi 5/bookworm 계열에서는 legacy `RPi.GPIO`/`pigpio`/구버전 pin mapping 코드가 깨질 수 있고, `gpiochip0`/`gpiochip4` 번호 차이나 libgpiod v1/v2 API 차이는 주의해야 한다. 하지만 이번 코드는 libgpiod v1 API로 실행되고 버튼 입력이 확인되었으므로 actuator 미동작의 1순위는 OS가 아니라 실드 actuator 전원/enable/interface/pin mapping이다.

## 25. 2026-06-25 SSAFY Smart Factory Shield 확인
- 사용자가 실드 모델명이 공개 상용 모델이 아니라 커스텀 제작 `SSAFY Smart Factory Shield`라고 확인했다.
- 따라서 인터넷/상용 모델명 기준 pin map 추정은 하지 않고, 보드 silkscreen/회로도/교육자료 또는 `gpiofind`/`gpioinfo`/`pinctrl` 기반 실측으로 pin mapping을 확정해야 한다.
- 현재 reference code의 가정은 `SERVO=GPIO18`, `DIR=GPIO17`, `STEP=GPIO27`, `ENABLE=GPIO22`, `BUTTON1/2=GPIO23/24`이다. 버튼이 동작하더라도 actuator pin mapping까지 맞다는 뜻은 아니므로, SSAFY 실드 회로도에서 서보/스텝 모터 입력이 실제로 이 GPIO들에 연결되는지 확인한다.
- 커스텀 실드에서는 버튼이 Pi GPIO에 직결되고, 스텝/서보는 별도 전원 rail, enable/standby, I2C PWM expander, motor driver input stage를 거칠 수 있으므로 `actuator 공통 계층` 우선순위를 유지한다.

## 26. 2026-06-25 `run_pi_controller.sh` 실행 로그 기반 코드 계층 최종 판정
- 사용자가 `./run_pi_controller.sh` 실행 로그를 공유했다. 로그상 `GPIO setup chip=gpiochip0 dir=17 step=27 enable=22 enable_active_low=True`, Modbus server 연결, `wrote status=0 error=0`, `motor step loop started direction=clockwise target_delay=0.0001000`, `wrote status=1 error=0`가 순서대로 확인되었다.
- 사용자가 `GPIO27`이 `lo/hi`로 계속 번갈아 바뀐다고 확인했다. 이는 `ConveyorMotor._run_loop()`가 실제로 STEP pulse를 지속 출력하고 있음을 의미한다.
- 공유된 Modbus response block은 `40021 command=1`, `40022 speed=100`, `40023 status=1`, `40024 error=0`, `40025 cube_detected=1`, `40026 cube_color=2`, `40027 last_vision_event=1`로 해석된다. 즉 controller는 run command를 읽고 running/no-error 상태를 쓰고 있다.
- `request ask for transaction_id=64 but got id=63`는 Modbus TCP transaction mismatch/stale response 경고로 기록하되, STEP pulse가 계속 나오고 상태가 running/error=0이므로 현재 모터 미동작의 1차 원인으로 보지 않는다.
- 로컬 검증: Pi controller tests `14 passed`. 현재 증거 기준 코드/Modbus/controller 계층은 정상 동작으로 판정하고, 남은 원인은 SSAFY Smart Factory Shield의 actuator 출력 계층 또는 실제 actuator pin mapping/전원/enable 쪽으로 좁힌다.

## 27. 2026-06-25 전원선 문제 해결 및 컨베이어 구동 확인
- 사용자가 최종 원인이 전원 문제였다고 확인했다. 다른 전원선을 사용하고 있어 actuator 전원이 정상 공급되지 않았고, 올바른 전원선으로 교체한 뒤 컨베이어가 정상 동작했다.
- 최종 판정: Modbus server/client, Raspberry Pi controller, `gpiod`, GPIO27 STEP pulse, command/status register 처리 코드는 정상. 실제 장애 원인은 SSAFY Smart Factory Shield/actuator 전원 공급 경로였다.
- 향후 같은 증상(`버튼은 동작하지만 스텝모터/서보모터가 모두 미동작`) 발생 시 우선 점검 순서: actuator 외부전원선/전원 rail/스위치/점퍼 → shield enable/standby → pin mapping → 코드/Modbus 순서로 본다.

## 28. 2026-06-25 D435i ROS raw ROI + WebSocket 결과 전송 전환
- 사용자가 D435i ROS 코드에서 top-view 보정을 생략하고 원본 RGB frame에서 바로 ROI를 적용하며, 결과 화면을 WebSocket server로 열어 다른 WebSocket client에 전송해야 한다고 요청했다.
- `conveyor_vision_test/topview_color_detector.py`에 `perspective_mode` parameter를 추가했다. 기본값은 `raw`이며, 기존 top-view 방식은 `perspective_mode:=topview` fallback으로 유지한다.
- raw ROI config `workspaces/지웅/conveyor/config/conveyor_roi_raw.json`을 추가했다. 현재 raw ROI는 기존 top-view source quad를 원본 frame ROI로 사용하며, 필요 시 실제 화면에서 더 타이트하게 재보정한다.
- WebSocket server 기능을 추가했다. 기본 `websocket_enabled:=true`, `websocket_host:=0.0.0.0`, `websocket_port:=28765`; client는 `ws://<PC_IP>:28765`로 접속해 JSON payload를 받는다. payload는 `type=conveyor_roi_result`, `frame_space`, `detections`, `modbus_state`, `image_jpeg_base64`를 포함한다.
- ROS executable alias `raw_roi_color_detector`를 추가했고 기존 `topview_color_detector`도 동일 entrypoint로 유지한다.
- 검증: ROS 환경에서 unit tests `15 passed`, `colcon build --packages-select conveyor_vision_test` 통과, `ros2 pkg executables conveyor_vision_test`에서 `raw_roi_color_detector` 확인, raw ROI smoke에서 `frame_space=raw`, shape `(720,1280,3)`, ROI `[[259,54],[983,54],[1208,600],[30,608]]` 확인.
- 현재 환경에는 `python3-websockets`가 설치되어 있지 않으므로 실제 WebSocket server 실행 전 `sudo apt install -y python3-websockets` 또는 해당 ROS Python 환경에 `websockets` 설치가 필요하다.

## 29. 2026-06-25 raw view ROI 좌표 재캡처 도구 추가
- raw-frame ROI를 실제 D435i 화면에서 다시 찍기 위해 `workspaces/지웅/conveyor/scripts/select_conveyor_raw_roi.py`를 추가했다.
- 이 도구는 top-view/perspective 단계를 거치지 않고 `/camera/camera/color/image_raw`에서 프레임을 freeze한 뒤 raw view에서 ROI 4점을 직접 클릭한다.
- 기본 출력은 `workspaces/지웅/conveyor/config/conveyor_roi_raw.json`이며, detector가 사용하는 `raw_roi.quad_xy_tl_tr_br_bl`과 `raw_roi.xyxy`를 갱신한다.
- preview 이미지는 `workspaces/지웅/conveyor/config/previews/conveyor_roi_raw_raw_roi.png`와 `..._raw_frame.png`에 저장된다.
- 실행 예:
  ```bash
  cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/conveyor
  source /opt/ros/humble/setup.bash
  python3 scripts/select_conveyor_raw_roi.py \
    --ros-topic /camera/camera/color/image_raw \
    --output config/conveyor_roi_raw.json \
    --display-scale 0.7
  ```
- 조작법: preview 창에서 SPACE로 현재 프레임 고정 → raw view에서 좌상단/우상단/우하단/좌하단 순서로 4점 클릭. 오른쪽 클릭 또는 `u`는 undo, `r`은 reset, `q`/ESC는 종료.
- 검증: `/usr/bin/python3 -m py_compile` 통과, `--help` 출력 확인, sample image 기반 `--self-test --output /tmp/conveyor_roi_raw_self_test.json` 통과.

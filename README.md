# SmartFarmProject

SSAFY에서 학습한 임베디드 로봇, 비전 AI, 컨베이어 제어, TurtleBot 자율주행, 웹 관제 요소를 통합한 스마트팜 자동화 프로젝트입니다.

## GitHub

- Repository: <https://github.com/akdlxm39/SmartFarmProject>
- Branch: `main`

## 현재 정리된 핵심 흐름

1. Dobot이 작물을 석션컵으로 수확한다.
2. 1번 카메라가 작물을 0 / 120 / -120도 방향에서 촬영한다.
3. 1번 카메라/비전 모델이 작물 종류 3종과 정상/불량 여부를 판정한다.
4. 불량 작물은 Dobot이 컨베이어 옆 불량품 상자에 투입한다.
5. 정상 작물만 컨베이어에 적재한다.
6. 2번 RGB-D/D435i 카메라는 컨베이어 정중앙 상단에서 아래를 바라보며 작물 존재/위치/흐름을 확인한다.
7. 정상 작물은 컨베이어 끝에서 낙하해 공용 정상 수거 상자에 담긴다.
8. TurtleBot은 MVP 범위에 포함하며 SLAM/자율주행 기반 물류 흐름을 담당한다.

## 통합 폴더 구조

최종 통합 실행 구조는 ROS2 workspace 관례에 맞춰 `workspace/src/` 아래에 둡니다. 단, 현재 진행 중인 작업 코드는 `workspaces/`에서 계속 작업하고, 검증된 시점에 아래 구조로 승격합니다.

```text
SmartFarmProject/
├── workspace/              # 통합 ROS2 workspace
│   └── src/
│       ├── apps/           # frontend/backend
│       ├── dobot/          # Dobot ROS2 package
│       ├── turtlebot/      # TurtleBot ROS2 package
│       ├── realsense/      # D435i/RealSense ROS2 package
│       ├── vision/         # Camera1 Pi, YOLO server 등 비ROS 비전 보조 프로세스
│       ├── conveyor/       # Raspberry Pi/GPIO/Modbus client 컨베이어 제어
│       ├── modbus/         # shared Modbus TCP register layer
│       ├── config/         # calibration, register maps
│       └── data/           # samples, models
├── docs/                   # project docs
├── references/             # planning/reference inputs
└── workspaces/             # 개인별 초기 작업 공간
```

`workspaces/`는 팀원별 초기 작업 공간으로 유지하고, 검증된 코드는 `workspace/src/` 아래 공통 구조로 단계적으로 승격합니다.

## `workspace/src` 목표 구조

```text
workspace/
└── src/
    ├── apps/
    │   ├── backend/
    │   └── frontend/
    ├── dobot/
    │   ├── package.xml
    │   ├── setup.py
    │   └── dobot/
    ├── turtlebot/
    │   ├── package.xml
    │   ├── setup.py
    │   └── turtlebot/
    ├── realsense/
    │   ├── package.xml
    │   ├── setup.py
    │   └── realsense/
    ├── vision/
    │   ├── camera1_pi/
    │   ├── yolo_server/
    │   └── README.md
    ├── conveyor/
    │   ├── pi_controller/
    │   ├── gpio/
    │   ├── modbus_client/
    │   └── README.md
    ├── modbus/
    │   └── shared_server/
    ├── config/
    │   ├── calibration/
    │   └── register_maps/
    └── data/
        ├── models/
        └── samples/
```

## 공통 실행 구조

### `workspace/src/apps/`
- `workspace/src/apps/frontend/`: Vue 기반 관제 대시보드
- `workspace/src/apps/backend/`: API/WebSocket/DB 연동 서버
- 초기 승격 후보: `workspaces/효진/smartfarm-pjt/`

### `workspace/src/dobot/`
- Dobot Magician ROS2 수확/촬영/분기 제어 package 위치
- `package.xml`, `setup.py`, `dobot/` Python package를 직접 둔다.
- 초기 승격 후보: `workspaces/지웅/ros2_ws/src/dobot_control_pkg/`

### `workspace/src/turtlebot/`
- TurtleBot SLAM/Navigation/배송 흐름 ROS2 package 위치
- `package.xml`, `setup.py`, `turtlebot/` Python package를 직접 둔다.

### `workspace/src/realsense/`
- D435i/RealSense 기반 컨베이어 감지 ROS2 package 위치
- `package.xml`, `setup.py`, `realsense/` Python package를 직접 둔다.
- 초기 승격 후보: `workspaces/지웅/ros2_ws/src/conveyor_vision_test/`

### `workspace/src/vision/`
- `workspace/src/vision/camera1_pi/`: 1번 카메라, 3방향 촬영, Pi Camera socket/JPG capture
- `workspace/src/vision/yolo_server/`: YOLO inference server/client
- 초기 승격 후보: `workspaces/지웅/vision/`, `workspaces/지성/yolov_wait/`

### `workspace/src/conveyor/`
- `workspace/src/conveyor/pi_controller/`: Raspberry Pi motor/servo 제어 로직
- `workspace/src/conveyor/gpio/`: GPIO 진단/테스트 도구
- `workspace/src/conveyor/modbus_client/`: Pi/PC 측 Modbus client 연동 코드
- 초기 승격 후보: `workspaces/지웅/conveyor/pi_controller/`, `workspaces/지웅/conveyor/scripts/`

### `workspace/src/modbus/`
- `workspace/src/modbus/shared_server/`: 공통 Modbus TCP server/register map

현재 기준:
- endpoint: `192.168.110.109:50200`
- Conveyor: `40021~40030`
- Dobot: `40031~40050`
- TurtleBot: `40051~40070`
- System/Farm: `40071~40100`

초기 승격 후보:
- `workspaces/지웅/modbus/`

### `workspace/src/config/`
- `workspace/src/config/calibration/`: Dobot 좌표, conveyor ROI 등 최신 calibration 기준 파일
- `workspace/src/config/register_maps/`: register map 문서/설정

### `workspace/src/data/`
- `workspace/src/data/samples/`: 작은 샘플 데이터
- `workspace/src/data/models/`: 모델 파일 관리 위치

주의: 대형 모델 파일과 runtime capture 결과는 Git LFS/Release asset/외부 저장소 사용을 검토합니다.

## 문서 구조

```text
docs/
├── 00_project/       # 프로젝트 개요, R&R, 착수 체크리스트
├── 10_architecture/  # 시스템 흐름, 아키텍처 계획, 현실/시뮬레이션 차이
├── 20_subsystems/    # vision, dobot, conveyor, modbus, turtlebot, web
├── 30_plans/         # WBS 검토, 구현 계획, 폴더 구조 정리 계획
├── 40_logs/          # 진행 로그, 결정 메모
└── diagrams/         # Excalidraw 등 다이어그램 산출물
```

주요 문서:
- `docs/00_project/프로젝트_개요_및_초기_정리.md`
- `docs/10_architecture/시스템_데이터_흐름_초안.md`
- `docs/10_architecture/아키텍처_보강_계획.md`
- `docs/20_subsystems/turtlebot/TurtleBot_작업_메모.md`
- `docs/30_plans/프로젝트_폴더_구조_정리_계획.md`
- `docs/30_plans/ROS2_workspace_src_구조_전환_계획.md`
- `docs/40_logs/진행_로그.md`
- `docs/40_logs/작업_결정_메모.md`
- `docs/diagrams/smartfarm_architecture_summary_v2.excalidraw`

## 개인 작업 폴더

초기 개발 단계에서는 팀원별 작업물을 `workspaces/`에 올리고, 뼈대가 잡힌 코드는 `workspace/src/` 공통 구조로 승격합니다.

- `workspaces/지성/`
- `workspaces/지웅/`
- `workspaces/효진/`

운영 규칙은 `workspaces/README.md`를 참고합니다.

## 현재 결정 사항

- 이 쓰레드 집중 범위: TurtleBot SLAM/Navigation/배송 흐름/Modbus 상태 연동
- TurtleBot MVP: 먼저 수동 주행 → SLAM/mapping → Nav2 단일 목표 이동 → 배송 상태/heartbeat 연동 순서로 검증
- TurtleBot 배송 호출/압력센서/상차 기구는 SLAM/Navigation 기본 성공 후 단계적으로 붙인다.
- TurtleBot Modbus block: `40051~40070` 예약, 상태/heartbeat부터 먼저 write하고 command/ack는 후속 단계로 확장
- 1번 카메라: 메인 판정 카메라
- 2번 카메라: 컨베이어 흐름 확인용 RGB-D/D435i 보조 비전 카메라
- 컨베이어 MVP: RGB 프레임 + raw ROI 기본, top-view는 fallback
- 컨베이어 제어: 큐브가 ROI 안에 보이면 Raspberry Pi/Modbus TCP로 시계방향 구동, 안정 미검출 시 정지
- Modbus server: `192.168.110.109:50200` shared register layer
- Raspberry Pi: 컨베이어 GPIO 제어와 실제 모터 상태 write(`40023/40024`)
- PC vision/manual client: 명령/비전 상태 write(`40021/40022/40025~40027`)
- 불량품 상자: 컨베이어 옆
- 정상 수거 상자: 컨베이어 끝
- 컨베이어 끝 구조: 낙하 방식
- 시뮬레이션: 현실 구현과 다르게 3열 분류 구조 유지
- 통합 실행 구조: `workspace/src/` 아래에 `apps/dobot/turtlebot/realsense/vision/conveyor/modbus/config/data`를 둔다.

## 다음 정리 예정

현재 작업 내용은 그대로 `workspaces/`에서 진행한다. 나중에 통합 요청이 오면 아래 순서로 선별 승격한다.

1. Frontend/backend prototype을 `workspace/src/apps/`로 승격
2. Dobot ROS2 package를 `workspace/src/dobot/`으로 승격
3. TurtleBot ROS2 package를 `workspace/src/turtlebot/`으로 승격
4. D435i/RealSense ROS2 package를 `workspace/src/realsense/`로 승격
5. Camera1/Pi Camera/JPG capture와 YOLO inference를 `workspace/src/vision/camera1_pi/`, `workspace/src/vision/yolo_server/`로 분리
6. Conveyor Pi/GPIO/Modbus client 코드를 `workspace/src/conveyor/` 하위로 분리
7. Modbus server를 `workspace/src/modbus/shared_server/`로 승격
8. Calibration/register/model 파일을 `workspace/src/config/`, `workspace/src/data/`로 정리

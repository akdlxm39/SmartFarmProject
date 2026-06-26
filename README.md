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

지금까지 `workspaces/`에서 진행한 코드를 `workspace/src/` 통합 실행 구조로 선별 승격했습니다. `workspaces/`는 개인별 작업 이력/원본 공간으로 보존하고, 실제 통합 실행 기준은 `workspace/src/`입니다.

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

## 통합된 코드 위치

### `workspace/src/apps/`
- `frontend/`: Vue 기반 관제 대시보드
- `backend/`: API/WebSocket/DB/Modbus 연동 서버 후보 구현
- 원본: `workspaces/효진/smartfarm-pjt/`

### `workspace/src/dobot/`
- Dobot Magician ROS2 수확/촬영/분기 제어 package
- 원본 `dobot_control_pkg`를 통합 package명 `dobot`으로 정리
- 주요 실행: `calibrate_positions`, `calibrate_harvest_positions`, `harvest_test`

### `workspace/src/turtlebot/`
- TurtleBot SLAM/Navigation/배송 흐름 ROS2 package
- 원본 `slam_pjt`를 통합 package명 `turtlebot`으로 정리
- map/config/docs/scripts 포함

### `workspace/src/realsense/`
- D435i/RealSense 기반 컨베이어 raw ROI/top-view 감지 ROS2 package
- 원본 `conveyor_vision_test`를 통합 package명 `realsense`로 정리
- ROI selector/helper scripts와 참고 RealSense 코드 포함

### `workspace/src/vision/`
- `camera1_pi/`: 1번 카메라 Pi/JPG capture/socket daemon
- `yolo_server/`: YOLO inference server/client

### `workspace/src/conveyor/`
- `pi_controller/`: Raspberry Pi motor/servo 제어 로직과 테스트
- `gpio/`: GPIO 진단/테스트 도구
- `modbus_client/`: Pi/PC 측 Modbus client/register map 코드
- `ref/`: 초기 실험/참고 conveyor 코드

### `workspace/src/modbus/`
- `shared_server/`: 공통 Modbus TCP server/register map
- endpoint 기준: `192.168.110.109:50200`
- register block: Conveyor `40021~40030`, Dobot `40031~40050`, TurtleBot `40051~40070`, System/Farm `40071~40100`

### `workspace/src/config/`, `workspace/src/data/`
- `config/calibration/`: Dobot 좌표, conveyor ROI 최신 JSON/MD
- `data/models/`: YOLO `best.pt`
- `data/samples/`: 샘플 데이터 위치

상세 원본→통합 위치는 `workspace/src/MIGRATION_MAP.md`에 기록했습니다.

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
- `docs/20_subsystems/turtlebot/TurtleBot_작업_메모.md`
- `docs/30_plans/ROS2_workspace_src_구조_전환_계획.md`
- `docs/40_logs/진행_로그.md`
- `workspace/src/MIGRATION_MAP.md`

## 개인 작업 폴더

`workspaces/`는 통합 전 개인별 작업 이력/원본 공간으로 유지합니다.

- `workspaces/지성/`
- `workspaces/지웅/`
- `workspaces/효진/`

## 현재 결정 사항

- 통합 실행 구조: `workspace/src/apps`, `workspace/src/dobot`, `workspace/src/turtlebot`, `workspace/src/realsense`, `workspace/src/vision`, `workspace/src/conveyor`, `workspace/src/modbus`, `workspace/src/config`, `workspace/src/data`
- TurtleBot MVP: 수동 주행 → SLAM/mapping → Nav2 단일 목표 이동 → 배송 상태/heartbeat 연동 순서
- 1번 카메라: 메인 판정 카메라
- 2번 카메라: 컨베이어 흐름 확인용 RGB-D/D435i 보조 비전 카메라
- 컨베이어 MVP: RGB 프레임 + raw ROI 기본, top-view는 fallback
- Modbus server: `192.168.110.109:50200` shared register layer
- 시뮬레이션: 현실 구현과 다르게 3열 분류 구조 유지

## 다음 작업

1. 실제 장비 연결 환경에서 각 subsystem 실행 smoke test
2. 필요 시 `workspace/src/` 기준 import/path 정리 추가
3. 통합 launch/runbook 작성

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

통합 실행 구조는 ROS2 package를 `workspace/src/` 바로 아래에 두는 방식으로 정리합니다.

```text
SmartFarmProject/
├── workspace/
│   └── src/
│       ├── apps/
│       │   ├── backend/
│       │   └── frontend/
│       ├── dobot/          # ROS2 package: Dobot Magician 제어
│       ├── turtlebot/      # ROS2 package: TurtleBot SLAM/Nav 자리
│       ├── realsense/      # ROS2 package: D435i conveyor ROI 감지
│       ├── vision/
│       │   ├── camera1_pi/ # Pi camera capture/socket daemon
│       │   └── yolo_server/# 1번 카메라 YOLO inference server
│       ├── conveyor/
│       │   ├── pi_controller/
│       │   ├── gpio/
│       │   └── modbus_client/
│       ├── modbus/
│       │   └── shared_server/
│       ├── config/
│       │   ├── calibration/
│       │   └── register_maps/
│       └── data/
│           ├── models/
│           └── samples/
├── docs/
├── references/
└── workspaces/
```

`workspaces/`는 팀원별 초기 작업 공간으로 유지하고, 검증된 코드는 `workspace/src/` 아래 공통 구조로 단계적으로 승격합니다.

## 공통 실행 구조

### `workspace/src/apps/`
- `backend/`: API/WebSocket/DB 연동 서버 prototype
- `frontend/`: Vue 기반 관제 대시보드 prototype

### `workspace/src/dobot/`
- `ros2 pkg create dobot --build-type ament_python ...` 기준 ROS2 package
- Dobot Magician 수확/촬영/분기 제어, 좌표 보정, 비전 캡처 요청 client

### `workspace/src/turtlebot/`
- `ros2 pkg create turtlebot --build-type ament_python ...` 기준 ROS2 package skeleton
- TurtleBot SLAM/Navigation/배송 흐름 노드 승격 예정

### `workspace/src/realsense/`
- `ros2 pkg create realsense --build-type ament_python ...` 기준 ROS2 package
- D435i/RealSense top-view/raw ROI 기반 컨베이어 흐름 확인

### `workspace/src/vision/`
- `camera1_pi/`: Raspberry Pi Camera client, PC capture server/daemon, socket protocol tests
- `yolo_server/`: 1번 카메라 3장 이미지 품질 판정용 YOLO inference server/client

### `workspace/src/conveyor/`
- `pi_controller/`: 저수준 motor/button helper, motion profile, 단위 테스트
- `gpio/`: Smart Factory Shield/GPIO actuator diagnostic scripts
- `modbus_client/`: shared Modbus server 명령을 읽어 conveyor GPIO를 구동하는 Raspberry Pi client

### `workspace/src/modbus/`
- `shared_server/`: 공통 Modbus TCP server/register map

현재 기준:
- endpoint: `192.168.110.109:50200`
- Conveyor: `40021~40030`
- Dobot: `40031~40050`
- TurtleBot: `40051~40070`
- System/Farm: `40071~40100`

### `workspace/src/config/`
- `calibration/`: Dobot 좌표, conveyor ROI 등 최신 calibration 기준 파일
- `register_maps/`: register map 문서/설정

### `workspace/src/data/`
- `samples/`: 작은 샘플 데이터
- `models/`: 모델 파일 관리 위치

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

- 1번 카메라: 메인 판정 카메라
- 2번 카메라: 컨베이어 흐름 확인용 RGB-D/D435i 보조 비전 카메라
- 컨베이어 MVP: RGB 프레임 + top-view 보정 + 단일 ROI + 빨강/초록 HSV 감지
- 컨베이어 제어: 큐브가 ROI 안에 보이면 Raspberry Pi/Modbus TCP로 시계방향 구동, 10프레임 연속 미검출되면 정지
- Modbus server: `192.168.110.109:50200` shared register layer
- Raspberry Pi: 컨베이어 GPIO 제어와 실제 모터 상태 write(`40023/40024`)
- PC vision/manual client: 명령/비전 상태 write(`40021/40022/40025~40027`)
- 불량품 상자: 컨베이어 옆
- 정상 수거 상자: 컨베이어 끝
- 컨베이어 끝 구조: 낙하 방식
- 시뮬레이션: 현실 구현과 다르게 3열 분류 구조 유지
- 통합 실행 구조: `workspace/src/` 아래에 직접 ROS2 package(`dobot`, `turtlebot`, `realsense`)와 기능별 비ROS 폴더(`vision`, `conveyor`, `modbus`, `apps`, `config`, `data`)를 둔다.

## 현재 통합 구조 반영 상태

요청한 구조 기준으로 재정리했다.

1. `dobot`, `turtlebot`, `realsense`는 `ros2 pkg create --build-type ament_python` 기반 package 구조로 생성/정리
2. Dobot 코드는 `workspace/src/dobot/`으로 승격
3. D435i/RealSense conveyor ROI 코드는 `workspace/src/realsense/`로 승격
4. Camera1 Pi capture/socket 코드는 `workspace/src/vision/camera1_pi/`로 승격
5. YOLO inference server/client는 `workspace/src/vision/yolo_server/`로 승격
6. Conveyor Pi 제어는 `workspace/src/conveyor/{pi_controller,gpio,modbus_client}/`로 분리
7. Modbus shared server와 config/data는 기존 `workspace/src/modbus`, `workspace/src/config`, `workspace/src/data` 기준 유지

상세 매핑은 `workspace/src/MIGRATION_MAP.md`를 기준으로 확인합니다.

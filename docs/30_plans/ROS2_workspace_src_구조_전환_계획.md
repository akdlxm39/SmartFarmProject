# ROS2 workspace/src 중심 구조 전환 계획

작성일: 2026-06-25
상태: skeleton 재배치 완료 / 실제 코드 승격 전

## 1. 배경

기존 1차 skeleton은 루트에 `apps/`, `robot/`, `vision/`, `embedded/`, `modbus/`, `config/`, `data/`를 두는 방식이었다.

하지만 프로젝트 특성상 Dobot, TurtleBot, D435i conveyor vision 등 ROS2 기반 요소가 많으므로, 통합 실행 구조는 ROS2 workspace 관례에 맞추는 편이 더 낫다.

따라서 통합 실행 구조를 아래처럼 수정한다.

```text
SmartFarmProject/
└── workspace/
    └── src/
        ├── apps/
        ├── robot/
        ├── vision/
        ├── embedded/
        ├── modbus/
        ├── config/
        └── data/
```

## 2. 핵심 결정

- ROS2 workspace 이름은 `workspace`로 둔다.
- 통합 대상 코드는 `workspace/src/` 아래에 모은다.
- 기존 `workspaces/`는 그대로 유지한다.
  - `workspaces/` = 개인별 초기 실험/작업 공간
  - `workspace/src/` = 통합 실행 구조
- `docs/`, `references/`는 루트에 유지한다.
- 실제 코드 승격은 아직 하지 않고, skeleton만 `workspace/src/`로 재배치했다.

## 3. 새 구조

```text
SmartFarmProject/
├── README.md
├── workspace/
│   ├── README.md
│   └── src/
│       ├── apps/
│       │   ├── README.md
│       │   ├── backend/
│       │   └── frontend/
│       ├── robot/
│       │   ├── README.md
│       │   ├── dobot/
│       │   └── turtlebot/
│       ├── vision/
│       │   ├── README.md
│       │   ├── camera1_inspection/
│       │   └── camera2_conveyor/
│       ├── embedded/
│       │   ├── README.md
│       │   └── conveyor_pi/
│       ├── modbus/
│       │   ├── README.md
│       │   └── shared_server/
│       ├── config/
│       │   ├── README.md
│       │   ├── calibration/
│       │   └── register_maps/
│       └── data/
│           ├── README.md
│           ├── models/
│           └── samples/
├── docs/
├── references/
└── workspaces/
    ├── 지성/
    ├── 지웅/
    └── 효진/
```

## 4. 이동 매핑 수정

### Web / Backend
| 현재 위치 | 이동 후보 |
|---|---|
| `workspaces/효진/smartfarm-pjt/src/` | `workspace/src/apps/frontend/src/` |
| `workspaces/효진/smartfarm-pjt/public/` | `workspace/src/apps/frontend/public/` |
| `workspaces/효진/smartfarm-pjt/package.json` | `workspace/src/apps/frontend/package.json` |
| `workspaces/효진/smartfarm-pjt/backend/` | `workspace/src/apps/backend/` |

### Vision Camera1
| 현재 위치 | 이동 후보 |
|---|---|
| `workspaces/지웅/vision/pc_jpeg_capture_server.py` | `workspace/src/vision/camera1_inspection/pc_capture_server/` |
| `workspaces/지웅/vision/raspi_jpeg_capture_client.py` | `workspace/src/vision/camera1_inspection/pi_camera_client/` |
| `workspaces/지웅/vision/vision_capture_daemon.py` | `workspace/src/vision/camera1_inspection/pc_capture_server/` |
| `workspaces/지성/yolov_wait/infer_server.py` | `workspace/src/vision/camera1_inspection/inference/` |
| `workspaces/지성/yolov_wait/infer_client.py` | `workspace/src/vision/camera1_inspection/inference/` |
| `workspaces/지성/yolov_wait/best.pt` | `workspace/src/data/models/` 또는 Git LFS/외부 링크 |

### Vision Camera2 / Conveyor
| 현재 위치 | 이동 후보 |
|---|---|
| `workspaces/지웅/conveyor/scripts/select_conveyor_roi.py` | `workspace/src/vision/camera2_conveyor/scripts/` |
| `workspaces/지웅/conveyor/config/conveyor_roi_topview.json` | `workspace/src/config/calibration/conveyor_roi_topview.json` |
| `workspaces/지웅/ros2_ws/src/conveyor_vision_test/` | `workspace/src/vision/camera2_conveyor/ros2_ws/src/conveyor_vision_test/` |

### Dobot
| 현재 위치 | 이동 후보 |
|---|---|
| `workspaces/지웅/ros2_ws/src/dobot_control_pkg/` | `workspace/src/robot/dobot/ros2_ws/src/dobot_control_pkg/` |
| `workspaces/지웅/ros2_ws/src/dobot_control_pkg/config/dobot_positions_latest.json` | `workspace/src/config/calibration/dobot_positions_latest.json` |

### Conveyor Pi
| 현재 위치 | 이동 후보 |
|---|---|
| `workspaces/지웅/conveyor/pi_controller/` | `workspace/src/embedded/conveyor_pi/controller/` |

### Modbus
| 현재 위치 | 이동 후보 |
|---|---|
| `workspaces/지웅/modbus/` | `workspace/src/modbus/shared_server/` |

## 5. 주의점

### ROS2 package 위치
`workspace/src/` 아래에 모든 것을 두더라도, 실제 `colcon build` 대상은 ROS2 package가 있는 경로여야 한다.

따라서 다음 중 하나를 선택해야 한다.

1. `workspace/src/robot/dobot/ros2_ws/src/dobot_control_pkg`처럼 기존 ROS2 workspace 구조를 보존한다.
2. `workspace/src/dobot_control_pkg`처럼 ROS2 package를 바로 `workspace/src` 아래로 끌어올린다.

현재는 팀별 작업 경로와 맥락을 보존하기 위해 **1번 방식**을 임시 기준으로 둔다.
추후 빌드가 불편하면 package를 더 평평하게 옮길 수 있다.

### 비ROS 코드
Frontend, backend, Modbus server, Raspberry Pi controller는 ROS2 package가 아닐 수 있다.
그래도 통합 관리 편의상 `workspace/src/` 아래에 두되, 각 README에 실행 방식을 분리해서 적는다.

## 6. 다음 실행 순서

1. 현재 변경사항 검토
2. 이 구조가 맞으면 commit/push
3. `workspace/src/modbus/shared_server/`부터 실제 코드 승격
4. 승격 후 smoke test
5. `workspace/src/embedded/conveyor_pi/` 승격
6. D435i conveyor vision / Dobot / Camera1 / Web 순서로 진행

## 7. 결론

새 기준은 다음 한 줄로 정리한다.

> 최종 통합 실행 구조는 `workspace/src/` 아래에 모으고, `workspaces/`는 개인별 초기 작업 공간으로 유지한다.

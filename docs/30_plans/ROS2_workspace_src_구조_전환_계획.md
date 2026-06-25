# ROS2 workspace/src 중심 구조 전환 계획

작성일: 2026-06-25
상태: 요청 구조 기준 재정리 완료

## 1. 배경

기존 1차 skeleton은 루트에 `apps/`, `robot/`, `vision/`, `embedded/`, `modbus/`, `config/`, `data/`를 두는 방식이었다.

하지만 프로젝트 특성상 Dobot, TurtleBot, D435i conveyor vision 등 ROS2 기반 요소가 많으므로, 통합 실행 구조는 ROS2 workspace 관례에 맞추는 편이 더 낫다.

따라서 통합 실행 구조를 아래처럼 수정한다.

```text
SmartFarmProject/
└── workspace/
    └── src/
        ├── apps/
        ├── dobot/
        ├── turtlebot/
        ├── realsense/
        ├── vision/
        ├── conveyor/
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
- 요청 구조 기준으로 `dobot`, `turtlebot`, `realsense`를 `ros2 pkg create --build-type ament_python` 기반 ROS2 package로 재정리했다.
- `vision/camera1_pi`, `vision/yolo_server`, `conveyor/pi_controller`, `conveyor/gpio`, `conveyor/modbus_client`로 비ROS 보조 프로세스를 분리했다.
- 원본 `workspaces/`는 개인별 작업 공간으로 보존한다.

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
│       ├── dobot/
│       │   ├── package.xml
│       │   ├── setup.py
│       │   └── dobot/
│       ├── turtlebot/
│       │   ├── package.xml
│       │   ├── setup.py
│       │   └── turtlebot/
│       ├── realsense/
│       │   ├── package.xml
│       │   ├── setup.py
│       │   └── realsense/
│       ├── vision/
│       │   ├── README.md
│       │   ├── camera1_pi/
│       │   └── yolo_server/
│       ├── conveyor/
│       │   ├── README.md
│       │   ├── pi_controller/
│       │   ├── gpio/
│       │   └── modbus_client/
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
| `workspaces/지웅/vision/pc_jpeg_capture_server.py` | `workspace/src/vision/camera1_pi/` |
| `workspaces/지웅/vision/raspi_jpeg_capture_client.py` | `workspace/src/vision/camera1_pi/` |
| `workspaces/지웅/vision/vision_capture_daemon.py` | `workspace/src/vision/camera1_pi/` |
| `workspaces/지성/yolov_wait/infer_server.py` | `workspace/src/vision/yolo_server/` |
| `workspaces/지성/yolov_wait/infer_client.py` | `workspace/src/vision/yolo_server/` |
| `workspaces/지성/yolov_wait/best.pt` | `workspace/src/data/models/` 또는 Git LFS/외부 링크 |

### Vision Camera2 / RealSense
| 현재 위치 | 이동 후보 |
|---|---|
| `workspaces/지웅/conveyor/scripts/select_conveyor_roi.py` | `workspace/src/realsense/scripts/` |
| `workspaces/지웅/conveyor/config/conveyor_roi_topview.json` | `workspace/src/config/calibration/conveyor_roi_topview.json` |
| `workspaces/지웅/ros2_ws/src/conveyor_vision_test/` | `workspace/src/realsense/` |

### Dobot
| 현재 위치 | 이동 후보 |
|---|---|
| `workspaces/지웅/ros2_ws/src/dobot_control_pkg/` | `workspace/src/dobot/` |
| `workspaces/지웅/ros2_ws/src/dobot_control_pkg/config/dobot_positions_latest.json` | `workspace/src/config/calibration/dobot_positions_latest.json` |

### Conveyor Pi
| 현재 위치 | 이동 후보 |
|---|---|
| `workspaces/지웅/conveyor/pi_controller/` | `workspace/src/conveyor/pi_controller/` + `workspace/src/conveyor/modbus_client/` |

### Modbus
| 현재 위치 | 이동 후보 |
|---|---|
| `workspaces/지웅/modbus/` | `workspace/src/modbus/shared_server/` |

## 5. 주의점

### ROS2 package 위치
`workspace/src/` 아래의 ROS2 package는 package root가 바로 `workspace/src/<package_name>/`에 오도록 둔다.

현재 기준:

1. `workspace/src/dobot` = Dobot Magician 제어 package
2. `workspace/src/turtlebot` = TurtleBot SLAM/Nav package skeleton
3. `workspace/src/realsense` = D435i/RealSense conveyor ROI 감지 package

이 구조에서는 `cd workspace && colcon build --packages-select dobot realsense turtlebot` 형태로 빌드한다.

### 비ROS 코드
Frontend, backend, Modbus server, Raspberry Pi controller는 ROS2 package가 아닐 수 있다.
그래도 통합 관리 편의상 `workspace/src/` 아래에 두되, 각 README에 실행 방식을 분리해서 적는다.

## 6. 다음 실행 순서

1. 현재 변경사항 검토
2. 이 구조가 맞으면 commit/push
3. 새 `workspace/src/` 기준으로 테스트/실행 경로 검증
4. import/path 차이를 발견하면 새 구조 기준으로 수정
5. 팀원 작업은 `workspaces/`에서 보존하면서 통합 코드는 `workspace/src/`에서 관리

## 7. 결론

새 기준은 다음 한 줄로 정리한다.

> 최종 통합 실행 구조는 `workspace/src/` 아래의 직접 ROS2 package(`dobot`, `turtlebot`, `realsense`)와 기능별 비ROS 폴더로 모으고, `workspaces/`는 개인별 초기 작업 공간으로 유지한다.

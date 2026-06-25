# ROS2 workspace/src 중심 구조 전환 계획

작성일: 2026-06-25
상태: 최종 목표 구조 확정 / 실제 코드 승격 전

## 1. 배경

기존 1차 skeleton은 루트에 `apps/`, `robot/`, `vision/`, `embedded/`, `modbus/`, `config/`, `data/`를 두는 방식이었다.

하지만 프로젝트 특성상 Dobot, TurtleBot, D435i/RealSense vision 등 ROS2 기반 요소가 많으므로, 통합 실행 구조는 ROS2 workspace 관례에 맞춰 `workspace/src/` 아래에 둔다.

추가 결정: ROS2 package는 `robot/dobot/ros2_ws/src/...`처럼 한 번 더 중첩하지 않고, `workspace/src/dobot`, `workspace/src/turtlebot`, `workspace/src/realsense`처럼 `workspace/src` 바로 아래에 둔다.

## 2. 핵심 결정

- ROS2 workspace 이름은 `workspace`로 둔다.
- 통합 대상 코드는 `workspace/src/` 아래에 모은다.
- Dobot, TurtleBot, RealSense는 `workspace/src/<package_name>/` 직접 ROS2 package 구조로 둔다.
- Camera1/Pi Camera와 YOLO server는 `workspace/src/vision/` 하위 비ROS 보조 프로세스로 둔다.
- Conveyor Raspberry Pi/GPIO/Modbus client 코드는 `workspace/src/conveyor/` 하위로 둔다.
- 기존 `workspaces/`는 그대로 유지한다.
  - `workspaces/` = 개인별 초기 실험/작업 공간
  - `workspace/src/` = 통합 실행 구조
- `docs/`, `references/`는 루트에 유지한다.
- 현재 작업 내용은 아직 옮기지 않고, 나중에 요청이 있을 때 선별 승격한다.

## 3. 최종 목표 구조

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

## 4. 이동 매핑 수정

### Web / Backend
| 현재 위치 | 이동 후보 |
|---|---|
| `workspaces/효진/smartfarm-pjt/src/` | `workspace/src/apps/frontend/src/` |
| `workspaces/효진/smartfarm-pjt/public/` | `workspace/src/apps/frontend/public/` |
| `workspaces/효진/smartfarm-pjt/package.json` | `workspace/src/apps/frontend/package.json` |
| `workspaces/효진/smartfarm-pjt/backend/` | `workspace/src/apps/backend/` |

### Dobot ROS2
| 현재 위치 | 이동 후보 |
|---|---|
| `workspaces/지웅/ros2_ws/src/dobot_control_pkg/` | `workspace/src/dobot/` |
| `workspaces/지웅/ros2_ws/src/dobot_control_pkg/config/dobot_positions_latest.json` | `workspace/src/config/calibration/dobot_positions_latest.json` |

### TurtleBot ROS2
| 현재 위치 | 이동 후보 |
|---|---|
| TurtleBot 작업 package | `workspace/src/turtlebot/` |

### RealSense / Conveyor ROS2 vision
| 현재 위치 | 이동 후보 |
|---|---|
| `workspaces/지웅/ros2_ws/src/conveyor_vision_test/` | `workspace/src/realsense/` |
| `workspaces/지웅/conveyor/scripts/select_conveyor_roi.py` | `workspace/src/realsense/scripts/` 또는 `workspace/src/conveyor/` 보조 도구 |
| `workspaces/지웅/conveyor/config/conveyor_roi_topview.json` | `workspace/src/config/calibration/conveyor_roi_topview.json` |

### Vision Camera1 / YOLO
| 현재 위치 | 이동 후보 |
|---|---|
| `workspaces/지웅/vision/pc_jpeg_capture_server.py` | `workspace/src/vision/camera1_pi/` |
| `workspaces/지웅/vision/raspi_jpeg_capture_client.py` | `workspace/src/vision/camera1_pi/` |
| `workspaces/지웅/vision/vision_capture_daemon.py` | `workspace/src/vision/camera1_pi/` |
| `workspaces/지성/yolov_wait/infer_server.py` | `workspace/src/vision/yolo_server/` |
| `workspaces/지성/yolov_wait/infer_client.py` | `workspace/src/vision/yolo_server/` |
| `workspaces/지성/yolov_wait/best.pt` | `workspace/src/data/models/` 또는 Git LFS/외부 링크 |

### Conveyor Pi / GPIO / Modbus client
| 현재 위치 | 이동 후보 |
|---|---|
| `workspaces/지웅/conveyor/pi_controller/` | `workspace/src/conveyor/pi_controller/` |
| `workspaces/지웅/conveyor/pi_controller/gpio_*diagnostic.py` | `workspace/src/conveyor/gpio/` |
| `workspaces/지웅/conveyor/pi_controller/conveyor_modbus_client_controller.py` | `workspace/src/conveyor/modbus_client/` |

### Modbus shared server
| 현재 위치 | 이동 후보 |
|---|---|
| `workspaces/지웅/modbus/` | `workspace/src/modbus/shared_server/` |

## 5. 주의점

### ROS2 package 위치
`colcon build` 편의성을 위해 실제 ROS2 package는 다음처럼 `workspace/src` 바로 아래에 둔다.

- `workspace/src/dobot/`
- `workspace/src/turtlebot/`
- `workspace/src/realsense/`

각 package 내부에는 `package.xml`, `setup.py`, Python package 디렉터리(`dobot/`, `turtlebot/`, `realsense/`)를 둔다.

### 비ROS 코드
Frontend, backend, Modbus server, Raspberry Pi controller, GPIO 진단 도구, YOLO server는 ROS2 package가 아닐 수 있다.
그래도 통합 관리 편의상 `workspace/src/` 아래에 두되, 실행 방식은 각 README에 분리해서 적는다.

### 현재 작업 내용 보존
현재 작업 중인 컨베이어/RealSense/Modbus 코드는 `workspaces/`에 그대로 둔다. 통합 구조로 옮기는 작업은 나중에 요청이 있을 때 다시 선별 진행한다.

## 6. 다음 실행 순서

1. 현재 작업은 `workspaces/`에서 계속 진행
2. 통합 요청이 오면 subsystem별로 승격 대상 파일 선별
3. ROS2 package는 `workspace/src/dobot`, `workspace/src/turtlebot`, `workspace/src/realsense` 직접 package 구조로 생성/정리
4. 비ROS 코드는 `apps`, `vision`, `conveyor`, `modbus`, `config`, `data` 하위로 분리
5. 승격 후 subsystem별 smoke test/pytest/colcon build 수행

## 7. 결론

새 기준은 다음 한 줄로 정리한다.

> 최종 통합 실행 구조는 `workspace/src/apps`, `workspace/src/dobot`, `workspace/src/turtlebot`, `workspace/src/realsense`, `workspace/src/vision`, `workspace/src/conveyor`, `workspace/src/modbus`, `workspace/src/config`, `workspace/src/data`이며, 현재 작업 내용은 나중에 요청이 있을 때 `workspaces/`에서 선별 승격한다.

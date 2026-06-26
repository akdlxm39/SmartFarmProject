# ROS 2 Workspace

이 폴더는 SmartFarmProject의 통합 실행 workspace입니다.

`workspaces/`에 있던 지금까지의 코드를 `workspace/src/` 아래 목표 구조로 선별 승격했습니다. 원본 `workspaces/`는 작업 이력/개인 작업 공간으로 보존합니다.

## 현재 구조

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

## 운영 원칙

- 통합 실행 기준은 `workspace/src/`입니다.
- ROS2 package는 `workspace/src/dobot`, `workspace/src/turtlebot`, `workspace/src/realsense`처럼 `workspace/src` 바로 아래에 둡니다.
- 비ROS 보조 프로세스는 `vision/`, `conveyor/`, `apps/`, `modbus/` 하위로 분리합니다.
- 상세 원본→통합 위치는 `workspace/src/MIGRATION_MAP.md`를 기준으로 합니다.

## 통합된 주요 영역

1. `workspace/src/apps/frontend`, `workspace/src/apps/backend`
2. `workspace/src/dobot/`
3. `workspace/src/turtlebot/`
4. `workspace/src/realsense/`
5. `workspace/src/vision/camera1_pi/`, `workspace/src/vision/yolo_server/`
6. `workspace/src/conveyor/pi_controller/`, `workspace/src/conveyor/gpio/`, `workspace/src/conveyor/modbus_client/`
7. `workspace/src/modbus/shared_server/`
8. `workspace/src/config/`, `workspace/src/data/`

# ROS 2 Workspace

이 폴더는 SmartFarmProject의 통합 실행 workspace입니다.

## 구조

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

- ROS2 package는 `workspace/src/` 바로 아래에 둡니다.
- `dobot`, `turtlebot`, `realsense`는 `/opt/ros/humble` 환경에서 `ros2 pkg create --build-type ament_python`로 만든 구조를 기준으로 합니다.
- 비ROS 보조 프로세스는 `vision/`, `conveyor/`, `modbus/`, `apps/`에 기능별로 둡니다.
- `workspaces/`는 팀원별 초기 실험/개인 작업 공간으로 유지합니다.
- 검증된 코드는 `workspaces/`에서 `workspace/src/`로 순차적으로 승격합니다.

상세 이동 매핑은 `workspace/src/MIGRATION_MAP.md`를 참고합니다.

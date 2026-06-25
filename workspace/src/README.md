# workspace/src 통합 실행 구조

이 디렉터리는 SmartFarmProject의 최종 통합 실행 기준입니다. ROS2 package는 `workspace/src/` 바로 아래에 두고, 비ROS 보조 프로세스는 기능별 폴더로 분리합니다.

```text
workspace/
└── src/
    ├── apps/
    │   ├── backend/
    │   └── frontend/
    ├── dobot/
    ├── turtlebot/
    ├── realsense/
    ├── vision/
    │   ├── camera1_pi/
    │   └── yolo_server/
    ├── conveyor/
    │   ├── pi_controller/
    │   ├── gpio/
    │   └── modbus_client/
    ├── modbus/
    │   └── shared_server/
    ├── config/
    └── data/
```

## ROS2 packages

`dobot`, `turtlebot`, `realsense`는 `/opt/ros/humble` 환경에서 `ros2 pkg create --build-type ament_python`로 생성한 ament_python package 구조를 기준으로 정리했습니다.

## 원본 보존

`workspaces/`는 팀원별 초기 작업/원본 보존 공간으로 유지합니다. 통합 실행과 빌드 검증은 이 `workspace/src/` 기준으로 진행합니다.

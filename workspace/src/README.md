# workspace/src 통합 실행 구조

이 디렉터리는 SmartFarmProject의 최종 통합 실행 구조입니다.
`workspaces/`에 있던 지금까지의 코드와 설정을 subsystem별로 선별 승격했습니다.

```text
workspace/src/
├── apps/                  # frontend/backend
├── dobot/                 # Dobot ROS2 package
├── turtlebot/             # TurtleBot ROS2 package + map/scripts
├── realsense/             # D435i/RealSense ROS2 package + ROI helpers
├── vision/                # Camera1 Pi/JPG capture, YOLO server
├── conveyor/              # Pi controller, GPIO diagnostics, Modbus client
├── modbus/                # shared Modbus TCP server/register map
├── config/                # calibration/register map artifacts
└── data/                  # model/sample assets
```

원본 `workspaces/`는 작업 이력/개인 작업 공간으로 보존합니다.

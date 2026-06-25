# ROS 2 Workspace

이 폴더는 SmartFarmProject의 통합 실행 workspace입니다.

## 구조

```text
workspace/
└── src/
    ├── apps/
    ├── robot/
    ├── vision/
    ├── embedded/
    ├── modbus/
    ├── config/
    └── data/
```

## 운영 원칙

- `workspace/src/` 아래에 통합 대상 코드를 모읍니다.
- ROS2 package는 각 subsystem 하위에 위치시키되, 필요한 경우 `colcon` 빌드 대상이 되도록 package 경로를 정리합니다.
- `workspaces/`는 팀원별 초기 실험/개인 작업 공간으로 유지합니다.
- 검증된 코드는 `workspaces/`에서 `workspace/src/`로 순차적으로 승격합니다. 현재 1차 승격본은 `workspace/src/MIGRATION_MAP.md`를 기준으로 확인합니다.

## 1차 승격 완료 영역

1. `workspace/src/modbus/shared_server/`
2. `workspace/src/embedded/conveyor_pi/controller/`
3. `workspace/src/vision/camera2_conveyor/`
4. `workspace/src/robot/dobot/`
5. `workspace/src/vision/camera1_inspection/`
6. `workspace/src/apps/frontend`, `workspace/src/apps/backend`

# workspace/src 통합 실행 구조

이 디렉터리는 개인별 `workspaces/`의 검증된 작업물을 통합 실행 기준으로 승격한 위치입니다.

## 현재 승격된 영역

- `apps/frontend/`: Vue 관제 대시보드 prototype
- `apps/backend/`: Web/backend prototype
- `modbus/shared_server/`: 공통 Modbus TCP server/register map
- `embedded/conveyor_pi/controller/`: Raspberry Pi conveyor Modbus client + GPIO controller
- `vision/camera2_conveyor/`: D435i/top-view conveyor vision ROS2 package, ROI scripts, requirements
- `robot/dobot/`: Dobot ROS2 control package
- `vision/camera1_inspection/`: Pi camera capture, PC capture server/daemon, YOLO inference client/server
- `config/calibration/`: Dobot 좌표와 conveyor ROI 기준 JSON/MD
- `config/register_maps/`: 공유 register map 문서 snapshot
- `data/models/`: inference model 파일

## 운영 원칙

- `workspace/src/`는 통합 실행 기준 경로입니다.
- `workspaces/`는 당분간 원본/개인 실험 공간으로 유지합니다.
- 새 기능은 가능한 한 `workspace/src/` 기준으로 경로를 맞추고, 필요 시 원본 경로와 동기화합니다.

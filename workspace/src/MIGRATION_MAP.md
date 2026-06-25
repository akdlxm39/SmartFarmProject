# workspace/src 승격 매핑

| 영역 | 원본 | 새 통합 위치 |
|---|---|---|
| Frontend | `workspaces/효진/smartfarm-pjt/` 중 backend 제외 | `workspace/src/apps/frontend/` |
| Backend | `workspaces/효진/smartfarm-pjt/backend/` | `workspace/src/apps/backend/` |
| Modbus server | `workspaces/지웅/modbus/` | `workspace/src/modbus/shared_server/` |
| Conveyor Pi | `workspaces/지웅/conveyor/pi_controller/` | `workspace/src/embedded/conveyor_pi/controller/` |
| Conveyor vision ROS2 | `workspaces/지웅/ros2_ws/src/conveyor_vision_test/` | `workspace/src/vision/camera2_conveyor/ros2_ws/src/conveyor_vision_test/` |
| Conveyor ROI scripts | `workspaces/지웅/conveyor/scripts/` | `workspace/src/vision/camera2_conveyor/scripts/` |
| Conveyor ROI config | `workspaces/지웅/conveyor/config/*.json` | `workspace/src/config/calibration/` |
| Dobot ROS2 | `workspaces/지웅/ros2_ws/src/dobot_control_pkg/` | `workspace/src/robot/dobot/ros2_ws/src/dobot_control_pkg/` |
| Dobot calibration | `workspaces/지웅/ros2_ws/src/dobot_control_pkg/config/dobot_positions_latest.*` | `workspace/src/config/calibration/` |
| Camera1 capture | `workspaces/지웅/vision/` | `workspace/src/vision/camera1_inspection/` |
| YOLO inference | `workspaces/지성/yolov_wait/` | `workspace/src/vision/camera1_inspection/inference/` + `workspace/src/data/models/best.pt` |

> 원본 `workspaces/`는 삭제하지 않고 보존합니다. 통합 실행/검증은 새 `workspace/src/` 기준으로 진행합니다.

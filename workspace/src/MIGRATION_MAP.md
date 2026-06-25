# workspace/src 승격 매핑

| 영역 | 원본 | 새 통합 위치 |
|---|---|---|
| Frontend | `workspaces/효진/smartfarm-pjt/` 중 backend 제외 | `workspace/src/apps/frontend/` |
| Backend | `workspaces/효진/smartfarm-pjt/backend/` | `workspace/src/apps/backend/` |
| Dobot ROS2 | `workspaces/지웅/ros2_ws/src/dobot_control_pkg/` | `workspace/src/dobot/` |
| TurtleBot ROS2 | 신규 ROS2 package skeleton | `workspace/src/turtlebot/` |
| RealSense/D435i ROS2 | `workspaces/지웅/ros2_ws/src/conveyor_vision_test/` | `workspace/src/realsense/` |
| Camera1 capture | `workspaces/지웅/vision/` | `workspace/src/vision/camera1_pi/` |
| YOLO inference | `workspaces/지성/yolov_wait/` | `workspace/src/vision/yolo_server/` + `workspace/src/data/models/best.pt` |
| Conveyor Pi helpers | `workspaces/지웅/conveyor/pi_controller/` | `workspace/src/conveyor/pi_controller/` |
| Conveyor GPIO diagnostics | `workspaces/지웅/conveyor/pi_controller/gpio_*`, `shield_*` | `workspace/src/conveyor/gpio/` |
| Conveyor Modbus client | `workspaces/지웅/conveyor/pi_controller/conveyor_modbus_client_controller.py` | `workspace/src/conveyor/modbus_client/` |
| Modbus server | `workspaces/지웅/modbus/` | `workspace/src/modbus/shared_server/` |
| Conveyor/Dobot calibration | `workspaces/지웅/.../config/*latest*`, `workspaces/지웅/conveyor/config/*.json` | `workspace/src/config/calibration/` |
| Register map docs | `workspaces/지웅/modbus/register_map.py` snapshot | `workspace/src/config/register_maps/` |

> 원본 `workspaces/`는 삭제하지 않고 보존합니다. 통합 실행/검증은 새 `workspace/src/` 기준으로 진행합니다.

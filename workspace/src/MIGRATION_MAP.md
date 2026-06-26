# workspace/src migration map

| 원본 | 통합 위치 | 비고 |
|---|---|---|
| `workspaces/효진/smartfarm-pjt/backend/` | `workspace/src/apps/backend/` | backend API/Modbus client |
| `workspaces/효진/smartfarm-pjt/` | `workspace/src/apps/frontend/` | Vue frontend, backend 제외 |
| `workspaces/지웅/ros2_ws/src/dobot_control_pkg/` | `workspace/src/dobot/` | ROS2 package 이름을 `dobot`으로 정리 |
| `workspaces/지웅/turtlebot/ros2_ws/src/slam_pjt/` | `workspace/src/turtlebot/` | ROS2 package 이름을 `turtlebot`으로 정리 |
| `workspaces/지웅/turtlebot/{config,docs,map,scripts}/` | `workspace/src/turtlebot/{config,docs,map,scripts}/` | TurtleBot 실행 보조 파일 |
| `workspaces/지웅/ros2_ws/src/conveyor_vision_test/` | `workspace/src/realsense/` | ROS2 package 이름을 `realsense`로 정리 |
| `workspaces/지웅/conveyor/scripts/` | `workspace/src/realsense/scripts/` | RealSense ROI selector/helper |
| `workspaces/지웅/vision/` | `workspace/src/vision/camera1_pi/` | Camera1 JPG capture/socket daemon |
| `workspaces/지성/yolov_wait/*.py,*.sh,README.md` | `workspace/src/vision/yolo_server/` | YOLO inference server/client |
| `workspaces/지성/yolov_wait/best.pt` | `workspace/src/data/models/best.pt` | 모델 파일 |
| `workspaces/지웅/conveyor/pi_controller/conveyor_motor.py` | `workspace/src/conveyor/pi_controller/` | motor/profile logic |
| `workspaces/지웅/conveyor/pi_controller/gpio_*`, `shield_*` | `workspace/src/conveyor/gpio/` | GPIO 진단 도구 |
| `workspaces/지웅/conveyor/pi_controller/*modbus*`, `register_map.py` | `workspace/src/conveyor/modbus_client/` | Pi Modbus client |
| `workspaces/지웅/conveyor/ref/conveyor/` | `workspace/src/conveyor/ref/conveyor/` | 참고/실험 코드 |
| `workspaces/지웅/conveyor/ref/realsense/` | `workspace/src/realsense/ref/` | 참고/실험 코드 |
| `workspaces/지웅/modbus/` | `workspace/src/modbus/shared_server/` | shared Modbus server/register map |
| `workspaces/지웅/ros2_ws/dobot_positions_latest.*` | `workspace/src/config/calibration/` | Dobot 최신 좌표 |
| `workspaces/지웅/conveyor/config/conveyor_roi_*.json` | `workspace/src/config/calibration/` | conveyor ROI calibration |

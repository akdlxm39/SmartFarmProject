# Camera2 Conveyor

2번 RGB-D/D435i 기반 컨베이어 흐름 확인 파이프라인입니다.

역할:
- 컨베이어 정중앙 상단 top-view
- ROI 기반 red/green HSV 감지
- 10프레임 미검출 시 정지 이벤트
- Modbus register write 연동

초기 승격 후보:
- `workspaces/지웅/conveyor/`
- `workspaces/지웅/ros2_ws/src/conveyor_vision_test/`

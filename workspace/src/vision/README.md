# Vision

비ROS 기반 1번 카메라 캡처/판정 보조 프로세스를 둡니다.

## 구조

- `camera1_pi/`: Raspberry Pi Camera client, PC capture server/daemon, socket protocol tests
- `yolo_server/`: 1번 카메라 3장 이미지 품질 판정용 YOLO inference server/client

2번 D435i/RealSense 컨베이어 ROI 감지는 ROS2 package인 `workspace/src/realsense/`에서 관리합니다.

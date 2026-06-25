# Camera1 Inspection

1번 카메라 기반 작물 검사 파이프라인입니다.

역할:
- Dobot 0/120/-120도 포즈별 JPG capture
- Pi Camera socket client/server
- YOLO inference 연동
- 작물 종류 + 정상/불량 판정

초기 승격 후보:
- `workspaces/지웅/vision/`
- `workspaces/지성/yolov_wait/`

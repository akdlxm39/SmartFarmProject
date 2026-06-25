# SmartFarmProject Architecture Summary v2

작성일: 2026-06-24

## Excalidraw
- File: `docs/diagrams/smartfarm_architecture_summary_v2.excalidraw`
- Absolute path: `/home/ssafy/work/SmartFarmProject/docs/diagrams/smartfarm_architecture_summary_v2.excalidraw`
- Hermes checkpoint: `28af6c9e491b4dd297`

> 다음부터 Excalidraw 작업은 링크만 주지 않고 `.excalidraw` 파일로 export/save한 뒤 경로를 함께 남긴다.

## 목적
한눈에 들어오는 대표 아키텍처 요약도.

## 이번 버전에서 강조한 것
1. 상단에는 실제 물리 처리 흐름을 먼저 배치했다.
   - 수확 영역 → Dobot → AI 판정 → 불량품 상자 / 컨베이어 → 정상 수거 상자 → TurtleBot 물류
2. 중앙에는 노트북 Main Hub를 배치했다.
   - FastAPI
   - Vision AI
   - ROS 2 Core
   - D435i Top-view ROI detector
3. 오른쪽에는 Edge/Device client를 배치했다.
   - Raspberry Pi Camera
   - Raspberry Pi Conveyor
   - Dobot ROS2 Node
   - TurtleBot Client
4. 하단에는 Modbus shared register layer를 별도로 배치했다.
   - server: `192.168.110.109:50200`
   - Conveyor: `40021~40030`
   - Dobot: `40031~40050`
   - TurtleBot: `40051~40070`
   - System/Farm: `40071~40100`
5. register ownership을 한눈에 보이게 분리했다.
   - PC Vision: `40021/40022/40025~40027`
   - Pi Conveyor: `40023/40024`

## 색상 범례
- 파랑: WebSocket / 영상 / UI
- 주황: Pi Camera socket JPG capture
- 분홍: ROS2
- 초록: Modbus TCP shared register
- 점선: 상태 피드백 / 예정 / 간접 연결

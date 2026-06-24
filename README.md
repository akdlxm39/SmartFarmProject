# SmartFarmProject

SSAFY에서 학습한 임베디드 로봇, 비전 AI, 컨베이어 제어, 웹 관제 요소를 통합한 스마트팜 자동화 프로젝트입니다.

## 현재 정리된 핵심 흐름
- Dobot이 작물을 석션컵으로 수확
- 1번 카메라가 작물을 120도 간격 3방향 촬영
- 1번 카메라/비전 모델이 작물 종류 3종 분류 + 불량 여부 판별
- 불량 작물은 Dobot이 별도 상자에 투입
- 정상 작물만 컨베이어에 적재
- 2번 카메라가 컨베이어 정중앙 상단에서 아래를 바라보며 작물 존재/위치/흐름 확인
- 정상 작물은 컨베이어 끝 공용 수거 상자로 이송

## 문서
- `docs/프로젝트_개요_및_초기_정리.md`
- `docs/시스템_데이터_흐름_초안.md`
- `docs/진행_로그.md`
- `docs/작업_결정_메모.md`
- `docs/Dobot_작업_메모.md`
- `docs/Vision_작업_메모.md`
- `docs/Conveyor_작업_메모.md`
- `docs/Conveyor_ROI_Modbus_구현_계획.md`
- `docs/Conveyor_Modbus_Async_RaspberryPi_전환_계획.md`
- `docs/Conveyor_Pi_Modbus_Client_Controller_구현_계획.md`
- `docs/Conveyor_Modbus_Server_작업_메모.md`
- `docs/Modbus_Server_작업_메모.md`

## Modbus 서버 작업공간
- `workspaces/지웅/modbus`: 공통 Modbus TCP server/shared register layer 관리 위치

## 개인 작업 폴더
초기 개발 단계에서는 팀원별 임시 작업 폴더에 코드를 올리고, 뼈대가 잡히면 공통 구조로 통합합니다.

- `workspaces/지성/`
- `workspaces/지웅/`
- `workspaces/효진/`

운영 규칙은 `workspaces/README.md`를 참고합니다.

## 현재 결정 사항
- 1번 카메라: 메인 판정 카메라
- 2번 카메라: 컨베이어 흐름 확인용 보조 비전 카메라
- 컨베이어 파트: D435i + OpenCV + 단일 ROI 기반으로 빨간색/녹색 큐브 존재 여부를 확인
- 컨베이어 D435i 입력: ROS 2 `realsense2_camera` 기반 통신
- 컨베이어 영상 처리: 원본 프레임에서 컨베이어 평면 4점을 클릭해 top-view로 보정한 뒤, 보정된 프레임 기준으로 `conveyor_roi`를 지정하고 ROI 내부에서만 색상 감지
- 컨베이어 제어: 빨강/초록 큐브는 같은 의미로 처리하며, 큐브가 ROI 안에 보이면 Raspberry Pi/Modbus TCP로 시계방향 구동, 10프레임 연속 미검출되면 정지
- Modbus: `pymodbus==3.13.1` 기준으로 운영하며, Modbus server는 `192.168.110.109:50200`의 shared register layer로 두고 PC/ROS2 vision node와 Raspberry Pi 5(`ssafy@192.168.110.139`)는 모두 client로 접속한다. Raspberry Pi는 컨베이어 GPIO 제어와 실제 모터 상태 write(`40023/40024`)를 담당하고, PC vision/manual client는 명령/비전 상태 write(`40021/40022/40025~40027`)를 담당한다. 추후 로봇 동작 상태와 농장 현황까지 관리하는 공통 상태/제어 레이어로 확장 예정이다
- 컨베이어 MVP: RGB 프레임 + top-view 보정 + 단일 ROI + 빨강/초록 HSV 감지 먼저 구현, depth는 필요 시 보조로 추가
- 불량품 상자: 컨베이어 옆
- 정상 수거 상자: 컨베이어 끝
- 컨베이어 끝 구조: 낙하 방식

## 다음 정리 예정
- Dobot 실제 좌표계/동작 시퀀스 구체화
- 상자/컨베이어 실제 배치도
- ROS 2 ↔ Django 연동 구조
- WBS 및 역할 분담

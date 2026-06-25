# SmartFarmProject Dobot 작업 메모

작성일: 2026-06-23
범위: 이 쓰레드의 우선 지원 대상은 **Dobot 파트**로 제한한다.

## 1. 현재 확정된 Dobot 기본 정보
- 모델: **Dobot Magician(두봇 매지션)**
- SDK/제어 방식: **ROS 2**
- ROS 2 패키지 기준: [`magician_ros2`](https://github.com/jkaniuka/magician_ros2) 빌드 완료 환경 기준
- 좌표 입력 순서: `(x, y, z)`
- HOME/READY 기준: `magician_ros2`에서 homing한 위치를 `(0, 0, 0)`으로 본다.
- 흡착 성공 여부 판단: **시간 기반 2초 대기**로 처리한다.
- jump move 안전 높이: **z = 100mm**
- HOME 복귀 위치: **(150, 0, 100)mm**
- 현재 비전 미연동 임시 동작: 비전 촬영 완료/판정 대기 코드는 주석 처리하고, 각 촬영 포즈에서 **2초 대기 후 다음 동작**으로 넘어간다.
- 3방향 촬영 방식: Dobot Magician 석션컵의 360도 회전을 이용한다.
  - `0도` 촬영
  - `120도` 회전 후 촬영
  - `-120도` 회전 후 촬영
  - 촬영 완료 후 다시 `0도`로 복귀

> 좌표 단위는 Dobot/ROS 2 제어 환경 기준값으로 사용한다. 실제 장비에서 충돌/도달 가능성 검증 후 보정한다. 특히 Dobot 위치를 옮기거나 homing 기준이 달라지면 TCP/실제 파지점 차이 때문에 좌표가 틀어질 수 있으므로, 장비 배치 후 현재 위치를 읽어 좌표를 다시 잡는다.

## 2. 현재 확정된 Dobot 역할
- 작물을 석션컵으로 흡착한다.
- 작물을 1번 카메라 촬영 위치로 이동한다.
- 석션컵 회전으로 0도/120도/-120도 3방향 촬영 포즈를 만든다.
- 1번 카메라 판정 결과를 기다린다.
- 판정 결과가 `불량`이면 컨베이어에 올리지 않고 불량품 상자 위에서 떨어뜨린다.
- 판정 결과가 `정상`이면 컨베이어 시작 위치에 올린다.

## 3. 확정 좌표
### 3.1 수확 위치 9개
| index | 좌표 `(x, y, z)` |
|---:|---|
| 1 | `(60, 180, -60)` |
| 2 | `(100, 180, -60)` |
| 3 | `(140, 180, -60)` |
| 4 | `(60, 220, -60)` |
| 5 | `(100, 220, -60)` |
| 6 | `(140, 220, -60)` |
| 7 | `(60, 260, -60)` |
| 8 | `(100, 260, -60)` |
| 9 | `(140, 260, -60)` |

### 3.2 주요 작업 위치
| 구분 | 좌표 `(x, y, z)` | 설명 |
|---|---|---|
| 촬영 위치 | `(240, 0, 0)` | 1번 카메라 앞 3방향 촬영 위치 |
| 불량품 상자 위치 | `(240, 140, 0)` | 위에서 석션 OFF로 떨어뜨림 |
| 컨베이어 시작점 위치 | `(160, -200, -10)` | 정상 작물 적재 위치 |
| 홈 위치 | `(150, 0, 100)` | 한 사이클 종료 후 복귀 위치 |

## 4. 현실 구현 기준 동작 시퀀스
1. `HOME/READY` 위치에서 대기
2. 수확 대상 index 선택
3. 해당 수확 좌표로 이동
4. 석션 ON
5. 시간 기반으로 2초 흡착 대기
6. jump move 방식으로 z=100mm까지 올린 뒤 촬영 위치 `(240, 0, 0)`으로 이동
7. 석션컵 각도 `0도` 설정 후 현재는 비전 호출 없이 2초 대기
8. 석션컵 각도 `120도` 설정 후 현재는 비전 호출 없이 2초 대기
9. 석션컵 각도 `-120도` 설정 후 현재는 비전 호출 없이 2초 대기
10. 석션컵 각도 `0도`로 복귀
11. 비전 판정 결과 수신 대기는 현재 주석 처리하고, 테스트용 분기값 또는 다음 동작으로 진행
12. `quality_status = defect`이면 불량품 상자 위치 `(240, 140, 0)`으로 이동 후 석션 OFF
13. `quality_status = normal`이면 컨베이어 시작점 `(160, -200, -10)`으로 이동 후 석션 OFF
14. 홈 위치 `(150, 0, 100)`으로 복귀

## 5. Dobot 상태값 초안
웹/로그/ROS 연동을 위해 최소한 아래 상태값을 맞춘다.

| 상태 | 의미 |
|---|---|
| `idle` | 대기 중 |
| `moving_to_crop` | 선택된 수확 좌표로 이동 중 |
| `suction_on` | 석션 ON 및 시간 기반 흡착 대기 |
| `moving_to_camera` | 1번 카메라 촬영 위치로 이동 중 |
| `pose_capture_0` | 석션컵 0도 촬영 포즈 |
| `pose_capture_120` | 석션컵 120도 촬영 포즈 |
| `pose_capture_minus_120` | 석션컵 -120도 촬영 포즈 |
| `rotating_to_0` | 촬영 후 석션컵 0도 복귀 중 |
| `waiting_vision_result` | 비전 판정 대기 |
| `moving_to_defect_box` | 불량품 상자로 이동 중 |
| `moving_to_conveyor` | 컨베이어 시작점으로 이동 중 |
| `release` | 석션 OFF / 작물 내려놓기 |
| `returning_home` | 홈 위치 복귀 중 |
| `error` | 예외 발생 |

## 6. 이동 방식 및 좌표 보정 원칙
### 6.1 HOME/좌표 기준
- `magician_ros2`에서 homing한 위치를 `(0, 0, 0)` 기준으로 사용한다.
- 단, ROS 2 통신만으로는 TCP/실제 파지점 위치 차이를 완전히 알기 어렵다.
- Dobot 본체 위치를 옮기거나 카메라/상자/컨베이어 배치를 바꾸면, 실제 파지점이 달라질 수 있다.
- 따라서 최종 배치 후에는 Dobot을 각 목표 위치로 직접 이동시킨 뒤 현재 위치를 읽어 좌표표를 다시 보정한다.

### 6.2 안전 이동 방식
- 바로 목표 좌표로 직선 이동하기보다 **jump move 방식**을 기본으로 한다.
- 기본 패턴:
  1. 현재 위치에서 z축을 안전 높이 `z=100mm`까지 올린다.
  2. 목표 위치의 x/y 방향으로 이동한다.
  3. 목표 z로 내려간다.
- 수확 위치 `z=-60`에서 촬영 위치나 상자 위치로 이동할 때도 중간 z 상승 waypoint를 사용한다.
- 현재 기준에서는 `z=100mm`를 기본 safe z로 사용한다.

## 7. ROS 2 인터페이스 초안
### 7.1 Dobot 제어 입력
- 수확 시작 명령
- 수확 대상 index: `1~9`
- 촬영 요청/완료 신호
- 비전 판정 결과: `inspection_id`, `crop_type`, `quality_status`
- 비상 정지/수동 중단 신호

### 7.2 Dobot 출력
- 현재 상태: `dobot_state`
- 현재 대상 수확 index
- 현재 목표 좌표
- 촬영 포즈 도달 완료: `0`, `120`, `-120`
- 정상/불량 목적지 투입 완료
- 에러 코드/에러 메시지

### 7.3 후보 토픽명
아직 최종 확정은 아니지만 ROS 2 기준으로 아래 이름을 후보로 둔다.

| 토픽 | 방향 | 내용 |
|---|---|---|
| `/dobot/harvest_command` | 입력 | 수확 시작, 대상 index |
| `/dobot/state` | 출력 | Dobot 현재 상태 |
| `/dobot/capture_pose_ready` | 출력 | 0/120/-120도 촬영 포즈 도달 알림 |
| `/vision/camera1/capture_done` | 입력 | 각도별 촬영 완료 알림 |
| `/vision/camera1/result` | 입력 | 작물 종류/정상·불량 판정 결과 |
| `/dobot/place_done` | 출력 | 불량품 상자 또는 컨베이어 적재 완료 |

### 7.4 `magician_ros2` 기본 인터페이스 참고
`magician_ros2` README 기준으로 실제 Dobot 제어/피드백에 우선 확인할 인터페이스는 아래와 같다.

| 인터페이스 | 타입/용도 | 메모 |
|---|---|---|
| `/dobot_homing_service` | service | homing 실행 |
| `/PTP_action` | action | PointToPoint 이동 명령. `target_pose`는 `[x, y, z, r]` 형식 |
| `/dobot_TCP` | topic | TCP pose, `geometry_msgs/msg/PoseStamped` |
| `/dobot_pose_raw` | topic | Dobot raw pose, `std_msgs/msg/Float64MultiArray` |
| `/dobot_suction_cup_service` | service | 석션컵 ON/OFF |

### 7.5 촬영 완료 신호 방식
- Dobot 노드는 각 촬영 각도에 도달하면 `/dobot/capture_pose_ready`로 `0`, `120`, `240` 중 현재 각도를 알린다.
- 비전 노드는 해당 각도 이미지를 촬영한 뒤 `/vision/camera1/capture_done`으로 완료를 응답한다.
- Dobot 노드는 각도별 완료 신호를 받은 뒤 다음 회전/이동 단계로 넘어간다.

현재는 비전 파트가 바로 붙어 있지 않으므로 위 촬영 완료 신호 대기 코드는 주석 처리한다. 임시 테스트에서는 각 촬영 각도 도달 후 2초 대기하고 다음 각도/동작으로 넘어간다.

## 8. 우선 구현 체크리스트
- [ ] Dobot Magician ROS 2 연결 확인
- [ ] HOME/READY 이동 확인
- [ ] 석션 ON/OFF 테스트
- [x] 수확 위치 9개 좌표 기록
- [x] 1번 카메라 촬영 위치 좌표 기록
- [x] 불량품 상자 좌표 기록
- [x] 컨베이어 시작점 좌표 기록
- [x] 0도/120도/-120도 촬영 방식 결정(240도는 action server에서 reject되어 -120도로 변경)
- [x] 흡착 성공 여부를 시간 기반 2초 대기로 시작하기로 결정
- [x] 촬영 완료 신호 방식 결정: Dobot 각도 도달 알림 → 비전 촬영 완료 응답
- [x] HOME/READY 기준 결정: `magician_ros2` homing 후 `(0, 0, 0)`
- [x] 안전 이동 방식 결정: jump move 방식으로 z축 상승 후 x/y 이동
- [x] jump move 안전 z 높이 결정: `z=100mm`
- [x] 비전 미연동 임시 방식 결정: 비전 호출/판정 대기 주석 처리 후 2초 대기
- [ ] 각 수확 좌표 reachability 확인
- [ ] 촬영 위치에서 0/120/-120도 회전 테스트
- [ ] 촬영 후 0도 복귀 테스트
- [ ] 정상/불량 분기 테스트
- [ ] 최종 장비 배치 후 현재 위치 읽기 기반 좌표 보정
- [ ] 비전 연동 재활성화 시 결과 대기 timeout 결정

## 9. 현재 열린 결정사항
1. 최종 좌표 보정 방식
   - Dobot을 실제 수확/촬영/상자/컨베이어 위치로 옮긴 뒤 `/dobot_TCP` 또는 `/dobot_pose_raw`에서 현재 위치를 읽는다.
   - 실제 사용할 피드백은 장비 연결 후 두 토픽의 값과 좌표 단위/기준이 현장 제어와 맞는지 확인해 선택한다.
   - 보정 후 이 문서의 좌표표를 최종 좌표로 갱신한다.
2. 비전 결과 대기 timeout
   - 현재는 비전 연동을 주석 처리하고 2초 대기로 대체한다.
   - 비전 노드가 붙은 뒤, 판정 결과를 반환하지 않을 때 몇 초 후 에러 처리할지 정한다.
3. 불량품 상자 투입 방식
   - `(240, 140, 0)`에서 바로 석션 OFF할지
   - 상자 위 안전 높이에서 떨어뜨릴지

## 10. WBS와의 연결
- `A4 로봇 시뮬레이션`: RoboDK에서 Dobot reachability와 촬영/분기 동작 검증
- `A7 HW 세팅(1)`: Dobot, 컨베이어 기본 조립 및 연결 확인
- `A12 모션 제어(수확)`: 수확 → 카메라 → 불량품 상자/컨베이어 분기 동작 구현
- `A15 시스템 연동`: Dobot 상태와 AI 판정 결과를 서버/로그로 전달

## 11. 다음 액션
1. `magician_ros2` 실행 후 `/dobot_TCP`, `/dobot_pose_raw`, `/PTP_action`, `/dobot_suction_cup_service`가 정상 노출되는지 확인한다.
2. 위 좌표 13개가 실제 장비에서 `z=100mm` jump move 방식으로 도달 가능한지 테스트한다.
3. 석션 ON 후 2초 대기 방식으로 작물 흡착 안정성을 확인한다.
4. 석션컵 회전 명령으로 0/120/-120도 제어 및 0도 복귀를 단독 테스트한다.
5. `harvest_index -> z=100mm jump move -> 석션 2초 -> 촬영 각도별 2초 대기 -> 임의 정상/불량 분기 -> 홈 복귀` 최소 ROS 2 테스트 노드를 작성한다.

## 12. 위치 재보정 도구
### 목적
- Dobot을 직접 손으로 움직여 실제 TCP 위치를 다시 잡는다.
- `/dobot_TCP` 토픽의 최신 pose를 `s` 입력 시점에 저장한다.
- 수확 위치는 `좌하단`, `우상단` 2개를 캡처한 뒤 3x3 격자로 자동 분할한다.

### 코드 위치
- ROS 2 노드: `workspaces/지웅/ros2_ws/src/dobot_control_pkg/dobot_control_pkg/calibrate_positions.py`
- ROS 2 실행 엔트리포인트: `calibrate_positions`
- 기본 결과 파일: `workspaces/지웅/ros2_ws/src/dobot_control_pkg/config/dobot_positions_latest.json`
- Markdown 요약: `workspaces/지웅/ros2_ws/src/dobot_control_pkg/config/dobot_positions_latest.md`

### 캡처 순서
1. 수확 영역 좌하단 위치
2. 수확 영역 우상단 위치
3. 촬영 위치
4. 불량품 상자 위치
5. 컨베이어 시작점 위치

### 실행 방법
```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run dobot_control_pkg calibrate_positions
```

### 사용 방법
각 단계에서:
1. 터미널 안내를 확인한다.
2. Dobot을 손으로 원하는 위치까지 움직인다.
3. 터미널에 `s`를 입력한다.
4. 노드가 그 순간의 `/dobot_TCP` 최신 위치를 저장한다.

### 출력 파일 활용
- `positions.harvest_grid`: 좌하단/우상단으로부터 생성된 수확 위치 9개
- `positions.camera`: 촬영 위치
- `positions.defect_box`: 불량품 상자 위치
- `positions.conveyor_start`: 컨베이어 시작점 위치
- `raw_captures`: 각 캡처 시점의 원본 `/dobot_TCP` pose와 선택적 `/dobot_pose_raw` 참조값

이 결과 파일을 기준으로 이후 Dobot 제어 코드의 위치 상수를 다시 조정한다.

## 13. 위치 재보정 결과 (2026-06-23)
### 검증 결과
- 위치 캡처 결과 파일이 생성되어 JSON 구조와 3x3 수확 격자 9개를 확인했다.
- 모든 캡처는 `/dobot_TCP` 최신 pose 기준이며, 저장 시점 age는 0.002~0.036초 범위로 정상이다.
- 기본 결과 파일은 `workspaces/지웅/ros2_ws/src/dobot_control_pkg/config/dobot_positions_latest.json`으로 복사해 두었다.
- 최초 실행 결과 원본도 `workspaces/지웅/ros2_ws/dobot_positions_latest.json`에 남아 있다.
- `/dobot_TCP` 좌표는 meter 단위로 저장되어 있으므로, 이후 제어 코드가 mm 단위를 요구하면 x/y/z에 1000을 곱해 반영한다.

### 수확 위치 3x3 (`/dobot_TCP`, meter)
| index | x | y | z |
|---:|---:|---:|---:|
| 1 | 0.0511 | 0.2006 | -0.0509 |
| 2 | 0.0794 | 0.2006 | -0.0509 |
| 3 | 0.1077 | 0.2006 | -0.0509 |
| 4 | 0.0511 | 0.1659 | -0.0509 |
| 5 | 0.0794 | 0.1659 | -0.0509 |
| 6 | 0.1077 | 0.1659 | -0.0509 |
| 7 | 0.0511 | 0.1312 | -0.0509 |
| 8 | 0.0794 | 0.1312 | -0.0509 |
| 9 | 0.1077 | 0.1312 | -0.0509 |

### 주요 위치 (`/dobot_TCP`, meter)
| 위치 | x | y | z |
|---|---:|---:|---:|
| 촬영 위치 | 0.2352 | -0.0028 | 0.0673 |
| 불량품 상자 | 0.1782 | 0.1138 | 0.0336 |
| 컨베이어 시작점 | 0.1041 | -0.1499 | 0.0183 |
| 홈 위치 | 0.1500 | 0.0000 | 0.1000 |

### mm 환산 참고
| 위치 | x(mm) | y(mm) | z(mm) |
|---|---:|---:|---:|
| harvest_1 | 51.1 | 200.6 | -50.9 |
| harvest_2 | 79.4 | 200.6 | -50.9 |
| harvest_3 | 107.7 | 200.6 | -50.9 |
| harvest_4 | 51.1 | 165.9 | -50.9 |
| harvest_5 | 79.4 | 165.9 | -50.9 |
| harvest_6 | 107.7 | 165.9 | -50.9 |
| harvest_7 | 51.1 | 131.2 | -50.9 |
| harvest_8 | 79.4 | 131.2 | -50.9 |
| harvest_9 | 107.7 | 131.2 | -50.9 |
| camera | 235.2 | -2.8 | 67.3 |
| defect_box | 178.2 | 113.8 | 33.6 |
| conveyor_start | 104.1 | -149.9 | 18.3 |
| home | 150.0 | 0.0 | 100.0 |

## 14. 단일 수확 테스트 노드
### 목적
- 사용자가 수확할 인덱스를 입력으로 선택한다.
- 선택된 수확 위치에서 작물을 흡착한 뒤 촬영 위치로 이동한다.
- 촬영 위치에서 `0도 -> 120도 -> -120도 -> 0도 복귀`를 수행하고, 각 촬영 각도에서 2초 대기한다.
- 비전 결과는 아직 붙이지 않고 **정상**으로 임시 분류해 컨베이어 시작점으로 이동한 뒤 석션을 OFF하고 홈으로 복귀한다.

### 코드 위치
- ROS 2 노드: `workspaces/지웅/ros2_ws/src/dobot_control_pkg/dobot_control_pkg/harvest_test.py`
- ROS 2 실행 엔트리포인트: `harvest_test`
- 참조 좌표 파일: `workspaces/지웅/ros2_ws/src/dobot_control_pkg/config/dobot_positions_latest.json`

### 인덱스 규칙
- 수확 인덱스는 캘리브레이션 원본 index가 아니라, **x 내림차순 -> y 내림차순**으로 다시 부여한다.
- 현재 실측 좌표 기준 인덱스표는 아래와 같다.

| 입력 index | 원본 위치 | x(mm) | y(mm) | z(mm) |
|---:|---|---:|---:|---:|
| 1 | harvest_3 | 107.7 | 200.6 | -50.0 |
| 2 | harvest_6 | 107.7 | 165.9 | -50.0 |
| 3 | harvest_9 | 107.7 | 131.2 | -50.0 |
| 4 | harvest_2 | 79.4 | 200.6 | -50.0 |
| 5 | harvest_5 | 79.4 | 165.9 | -50.0 |
| 6 | harvest_8 | 79.4 | 131.2 | -50.0 |
| 7 | harvest_1 | 51.1 | 200.6 | -50.0 |
| 8 | harvest_4 | 51.1 | 165.9 | -50.0 |
| 9 | harvest_7 | 51.1 | 131.2 | -50.0 |

### 실행 방법
```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/ros2_ws
source /opt/ros/humble/setup.bash
source /home/ssafy/ros2/magician_ros2_control_system_ws/install/setup.bash
source install/setup.bash
ros2 run dobot_control_pkg harvest_test
```

특정 인덱스를 바로 실행하려면:
```bash
ros2 run dobot_control_pkg harvest_test --harvest-index 1
```

실제 동작 없이 순서만 확인하려면:
```bash
ros2 run dobot_control_pkg harvest_test --dry-run --harvest-index 1 --yes
```

### 현재 구현 시퀀스
1. `x 내림차순 -> y 내림차순` 기준 수확 인덱스표 출력
2. 사용자 인덱스 입력
3. `z=100mm` jump move로 수확 위치 접근
4. 석션 ON, 2초 대기
5. `z=100mm` jump move로 촬영 위치 이동
6. 촬영 위치에서 `r=0`, `r=120`, `r=-120` 각도별 2초 대기
7. `r=0` 복귀
8. 임시 결과를 정상으로 고정
9. `z=100mm` jump move로 컨베이어 시작점 이동
10. 석션 OFF
11. 홈 위치 `(150, 0, 100)`으로 복귀

### 검증
- `python3 -m py_compile workspaces/지웅/ros2_ws/src/dobot_control_pkg/dobot_control_pkg/harvest_test.py` 통과
- `colcon build --packages-select dobot_control_pkg` 통과
- `ros2 run dobot_control_pkg harvest_test --help` 통과
- `ros2 run dobot_control_pkg harvest_test --dry-run --harvest-index 9 --yes`로 x/y 정렬 인덱스와 시퀀스 출력 확인

## 15. 수확 위치 9점 재보정 도구
### 변경 이유
- 좌하단/우상단 2점만 찍고 3x3으로 분할한 결과가 실제 수확 위치와 맞지 않았다.
- 따라서 수확 위치는 9개를 모두 직접 찍어서 보정한다.
- 수확 z는 현장 테스트 기준 **-50mm**로 고정한다.

### 코드 위치
- ROS 2 노드: `workspaces/지웅/ros2_ws/src/dobot_control_pkg/dobot_control_pkg/calibrate_harvest_positions.py`
- ROS 2 실행 엔트리포인트: `calibrate_harvest_positions`
- 갱신 대상 파일: `workspaces/지웅/ros2_ws/src/dobot_control_pkg/config/dobot_positions_latest.json`

### 실행 방법
```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/ros2_ws
source /opt/ros/humble/setup.bash
source /home/ssafy/ros2/magician_ros2_control_system_ws/install/setup.bash
source install/setup.bash
ros2 run dobot_control_pkg calibrate_harvest_positions
```

### 동작 방식
1. 인덱스 기준은 **x 내림차순 -> y 내림차순**이다.
2. `harvest_1`부터 `harvest_9`까지 각 위치를 직접 맞춘다.
3. 각 위치에서 `s`를 입력하면 최신 `/dobot_TCP` pose를 저장한다.
4. x/y는 실측값을 쓰고, z는 기본값 `-50mm`로 저장한다.
5. 기존 `dobot_positions_latest.json`의 촬영/불량상자/컨베이어 위치는 유지하고, `positions.harvest_grid`만 새 9점 값으로 교체한다.
6. 덮어쓰기 전 timestamp backup JSON을 만든다.

### 관련 제어 코드 변경
- `harvest_test.py`는 수확 z를 기본 `-50mm`로 사용하도록 변경했다.
- 촬영 회전은 `240도`가 reject되어 `0도 -> 120도 -> -120도 -> 0도 복귀`로 변경했다.

### 검증
- `python3 -m py_compile calibrate_harvest_positions.py harvest_test.py` 통과
- `colcon build --packages-select dobot_control_pkg` 통과
- `ros2 run dobot_control_pkg calibrate_harvest_positions --help` 통과
- `ros2 run dobot_control_pkg harvest_test --dry-run --harvest-index 1 --yes --wait-sec 0.01`에서 `z=-50.0`, `r=-120.0` 반영 확인

## 16. 수확 위치 9점 보정 후 테스트 준비
### 최신 수확 위치
- 갱신 시각: `2026-06-23T15:00:33`
- 기준 파일: `workspaces/지웅/ros2_ws/src/dobot_control_pkg/config/dobot_positions_latest.json`
- 인덱스 기준: **x 내림차순 -> y 내림차순**
- 수확 z: **-50mm 고정**
- 홈 위치: **(150, 0, 100)mm**
- 기본 safe z: **100mm**

| 입력 index | 원본 위치 | x(mm) | y(mm) | z(mm) | measured_z(mm) |
|---:|---|---:|---:|---:|---:|
| 1 | harvest_1 | 116.8 | 206.1 | -50.0 | -48.4 |
| 2 | harvest_2 | 114.0 | 169.3 | -50.0 | -47.1 |
| 3 | harvest_3 | 106.2 | 131.2 | -50.0 | -46.6 |
| 4 | harvest_4 | 82.9 | 203.4 | -50.0 | -47.8 |
| 5 | harvest_5 | 79.4 | 163.2 | -50.0 | -46.8 |
| 6 | harvest_6 | 74.0 | 125.1 | -50.0 | -44.9 |
| 7 | harvest_7 | 51.2 | 198.9 | -50.0 | -47.0 |
| 8 | harvest_8 | 47.8 | 161.2 | -50.0 | -45.9 |
| 9 | harvest_9 | 45.0 | 122.4 | -50.0 | -45.5 |

### z축 상승 의심 이슈 대응
- 관찰: 이전 동작에서 z축 상승이 충분히 보이지 않았다.
- 코드 측 원인 후보: 기존 `harvest_test.py`는 첫 이동 전에 현재 Dobot TCP 위치를 모르기 때문에, 첫 `jump_move_to()`에서 “현재 x/y에서 z만 상승”하지 못하고 곧바로 “목표 x/y, safe z”로 이동할 수 있었다.
- 대응: 실제 동작 모드에서는 시작 전 `/dobot_TCP`를 읽어 `current_pose`를 초기화하도록 수정했다.
- 효과: 첫 이동도 `현재 x/y -> safe z`를 먼저 수행한 뒤 `목표 x/y -> 목표 z` 순서로 진행한다.
- 기본 safe z는 `100mm`로 변경했다. 만약 이 수정 후에도 높이가 부족하면 `--safe-z-mm 120`처럼 더 올려서 테스트한다.

### 수정 후 검증
- `python3 -m py_compile harvest_test.py calibrate_harvest_positions.py` 통과
- `colcon build --packages-select dobot_control_pkg` 통과
- `ros2 run dobot_control_pkg harvest_test --dry-run --harvest-index 1 --yes --wait-sec 0.01`에서 최신 9점 좌표, `z=-50.0`, `r=-120.0`, safe z 이동 로그 확인

## 17. 홈 위치와 safe z 기본값 변경
- JSON `positions.home`에 홈 위치를 추가했다: `(x=0.15, y=0.0, z=0.1)m` = `(150, 0, 100)mm`.
- `harvest_test.py`의 `--safe-z-mm` 기본값을 `100`으로 변경했다.
- 한 사이클 종료 후 `conveyor_start`에서 석션 OFF한 뒤 홈 위치로 복귀하도록 변경했다.

## 18. 비전 소켓 연동 분리 계획
- 계획 문서: `docs/Dobot_비전_소켓_연동_계획.md`
- 방향: `harvest_test.py`는 Dobot 이동/석션/회전과 “촬영 요청 타이밍”만 담당하고, 라즈베리파이 소켓 통신은 별도 PC 데몬이 담당한다.
- 신규 분리 후보:
  - `workspaces/지웅/vision/vision_socket_protocol.py`: JPG 패킷/JSON line 공통 프로토콜
  - `workspaces/지웅/vision/vision_capture_daemon.py`: 라즈베리파이 연결 유지 + 로컬 캡처 요청 처리
  - `workspaces/지웅/ros2_ws/src/dobot_control_pkg/dobot_control_pkg/vision_capture_client.py`: Dobot 노드에서 호출하는 얇은 로컬 클라이언트
- 권장 흐름: 각도 `0/120/-120` 도달 후 `harvest_test.py`가 로컬 데몬에 capture 요청을 보내고, 데몬이 라즈베리파이에 JPG 촬영 명령을 전달한 뒤 저장 경로를 반환한다.

## 19. 비전 소켓 연동 구현 결과
- 구현 파일:
  - `workspaces/지웅/vision/vision_socket_protocol.py`
  - `workspaces/지웅/vision/vision_capture_daemon.py`
  - `workspaces/지웅/vision/run_vision_capture_daemon.sh`
  - `workspaces/지웅/ros2_ws/src/dobot_control_pkg/dobot_control_pkg/vision_capture_client.py`
  - `workspaces/지웅/ros2_ws/src/dobot_control_pkg/dobot_control_pkg/harvest_test.py`
- `harvest_test.py`에 `--vision-mode wait|socket|off`, `--vision-host`, `--vision-port`, 캡처 해상도/품질 옵션을 추가했다.
- `--vision-mode socket`에서는 촬영 각도 `0/120/-120`마다 로컬 비전 데몬에 캡처 요청을 보낸다.
- 3장 캡처가 모두 성공하면 현재 테스트 목적상 `quality_status=normal`로 판정한다.
- 판정 결과가 `normal`이면 컨베이어 시작점으로 이동 후 석션 OFF, `defect`이면 불량품 상자로 이동 후 석션 OFF한다.
- 검증:
  - vision pytest 1개 통과
  - dobot pytest 3개 통과
  - 기존 `smoke_jpeg_command.sh` 통과
  - `colcon build --packages-select dobot_control_pkg` 통과
  - `ros2 run ... --dry-run --vision-mode socket` + mock Pi 클라이언트에서 3장 저장 및 NORMAL→컨베이어 분기 확인

## 20. 비전 소켓 연결 끊김 원인 및 수정
- 현상: Dobot 노드가 첫 촬영 요청을 보낼 때 `ConnectionError: socket closed while receiving 16 bytes`가 발생했다.
- 원인: 라즈베리파이 클라이언트가 `socket.create_connection(..., timeout=10)`으로 연결한 뒤 그 timeout이 명령 대기 `readline()`에도 남아 있었다. Dobot 이동 시간이 10초를 넘으면 클라이언트가 `TimeoutError`로 연결을 끊고 `--reconnect`로 새 연결을 반복했다.
- 데몬은 최초 Pi 소켓 하나만 사용하고 있었기 때문에, 죽은 소켓에 캡처 명령을 보내면서 16-byte 헤더 수신 실패가 발생했다. 즉, 두 소켓 구조 자체의 문제가 아니라 Pi 명령 대기 timeout과 데몬의 재연결 처리 부족이 원인이었다.
- 수정:
  - `raspi_jpeg_capture_client.py`에 `--connect-timeout-sec`, `--command-idle-timeout-sec`를 추가했다.
  - 기본 `--command-idle-timeout-sec 0`은 명령 대기 timeout 없음이다.
  - `vision_capture_daemon.py`가 Pi 소켓 실패 시 한 번 새 Pi 연결을 accept하고 같은 요청을 재시도하도록 보강했다.
- 검증: Pi 클라이언트가 10초 이상 명령 없이 대기한 뒤 캡처 요청을 받아 성공하는 회귀 테스트와 `ros2 run ... --dry-run --vision-mode socket` 3장 캡처 테스트를 통과했다.

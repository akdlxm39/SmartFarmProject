# TurtleBot 작업 메모

작성일: 2026-06-25  
범위: TurtleBot SLAM / Navigation / 배송 흐름 / Modbus 상태 연동

## 1. 이 문서의 목적

이 문서는 SmartFarmProject에서 TurtleBot 파트를 별도 집중 범위로 다루기 위한 실행 메모다.

이번 쓰레드에서는 TurtleBot 파트만 집중한다. Dobot, 컨베이어, 비전, 웹/서버는 TurtleBot이 배송 흐름을 시작하거나 상태를 주고받는 **인터페이스 의존성** 수준에서만 언급한다.

## 2. 확인한 기존 문서 요약

확인한 기준 문서:

- `README.md`
- `docs/00_project/R&R_초안.md`
- `docs/30_plans/WBS_검토_메모.md`
- `docs/30_plans/WBS_재검토_메모.md`
- `docs/40_logs/진행_로그.md`
- `docs/40_logs/작업_결정_메모.md`
- `docs/10_architecture/시스템_데이터_흐름_초안.md`
- `docs/20_subsystems/modbus/Modbus_Register_Map_확장_계획.md`
- `docs/20_subsystems/turtlebot/README.md`
- Obsidian `프로젝트 개요 및 목표`, `진행 로그`, `작업 결정 메모`

현재 문서 기준 핵심 사실:

- TurtleBot은 MVP 범위에 포함되어 있다.
- WBS의 자율주행 축은 TurtleBot SLAM, 맵핑, 목표 지점 이동/배송 흐름을 포함한다.
- R&R 기준 TurtleBot은 `Participant2 — 로봇/시뮬레이션/자율주행 리드`의 담당 축에 포함된다.
- 3인 프로젝트 일정 리스크를 줄이기 위해 TurtleBot은 **SLAM/주행 자체를 먼저 성공**시키고, 압력센서/상차/배송 호출은 단계적으로 붙이는 방향이 안전하다.
- Modbus shared register layer에는 TurtleBot block `40051~40070`이 예약되어 있다.
- `workspace/src/robot/turtlebot/`와 `docs/20_subsystems/turtlebot/`는 아직 skeleton 수준이다.
- 현재 프로젝트의 실제 작업 코드는 `workspaces/`에서 계속 진행하고, 검증 후 `workspace/src/`로 승격한다.

## 3. 현재 범위 결정

### 이번 TurtleBot 집중 범위

이번 범위에서 우선 다룰 것:

1. TurtleBot 실행 환경 확인
2. SLAM / mapping 기본 성공
3. Navigation2 기반 목표 지점 이동 기본 성공
4. 배송 시작/도착/복귀 흐름의 최소 상태 정의
5. Modbus `40051~40070` block에 TurtleBot 상태 heartbeat를 쓰는 최소 client 설계
6. Web/backend 또는 orchestrator가 향후 배송 명령을 줄 수 있도록 command/ack 패턴 정리

이번 범위에서 후순위로 미룰 것:

- 실제 컨베이어 끝 상자와 TurtleBot 적재 기구의 정교한 메커니즘
- 압력센서 임계치 기반 자동 배송 호출
- 웹 대시보드 상세 UI
- 전체 시스템 orchestrator 완성
- 시뮬레이션 3열 분류 구조와 현실 물류 구조의 완전 통합

## 4. TurtleBot MVP 실행 순서 초안

TurtleBot만 떼어서 보면 다음 순서가 가장 안전하다.

1. **환경 확인**
   - TurtleBot 모델/ROS 2 distro 확인
   - bringup 명령 확인
   - LiDAR, odom, TF, battery topic 확인

2. **수동 주행 smoke test**
   - teleop 또는 `/cmd_vel`로 전/후/회전 기본 동작 확인
   - 비상정지/정지 명령 확인

3. **SLAM / mapping**
   - 작업 공간 맵 생성
   - map 저장 경로 확정
   - 저장된 map을 repo/Obsidian 문서에 기록

4. **Navigation2 목표 이동**
   - `home`, `pickup_wait`, `delivery_goal` 같은 최소 waypoint 후보 지정
   - 한 개 goal로 이동 성공 확인
   - 도착/실패/취소 상태 확인

5. **배송 흐름 최소화**
   - `deliver_start -> navigating -> arrived -> delivering -> return_home -> idle` 흐름으로 시작
   - 실제 상차 구조가 없어도, 초기에는 도착 이벤트/대기 시간으로 배송 완료를 모의 처리

6. **Modbus heartbeat/status 연동**
   - TurtleBot client가 `40055 turtlebot_status`, `40057 turtlebot_nav_state`, `40058 turtlebot_battery_percent`, `40059 turtlebot_current_goal`, `40063 turtlebot_heartbeat`를 주기적으로 write
   - command 실행은 heartbeat smoke가 안정화된 뒤 `40051~40054` command/ack로 확장

## 5. TurtleBot 상태/이벤트 초안

### 상태 enum 초안

`40055 turtlebot_status` 후보:

| 값 | 상태 | 의미 |
|---:|---|---|
| 0 | idle | 대기 |
| 1 | navigating | 목표 지점으로 이동 중 |
| 2 | arrived | 목표 지점 도착 |
| 3 | delivering | 배송/하차 처리 중 |
| 4 | paused | 일시정지 |
| 5 | error | 오류 |

### command enum 초안

`40051 turtlebot_command` 후보:

| 값 | 명령 | 의미 |
|---:|---|---|
| 0 | none | 명령 없음 |
| 1 | deliver_start | 배송 시작 |
| 2 | pause | 일시정지 |
| 3 | resume | 재개 |
| 4 | return_home | 복귀 |
| 5 | stop | 정지 |
| 6 | reset | 오류/상태 초기화 |

## 6. 인터페이스 의존성

### Dobot / Conveyor와의 관계

- Dobot은 정상 판정 작물을 컨베이어 시작점에 올린다.
- 컨베이어는 정상 작물을 끝단 공용 수거 상자 방향으로 이송한다.
- TurtleBot은 컨베이어 이후 물류/배송 흐름을 담당한다.
- 다만 TurtleBot 1차 구현은 컨베이어 물리 상차가 완성되기 전에도 SLAM/Navigation 자체를 독립 검증한다.

### Web/backend/orchestrator와의 관계

- Web은 직접 TurtleBot 세부 topic을 제어하기보다 `system_command` 또는 orchestrator를 통해 배송 명령을 내리는 구조가 안전하다.
- TurtleBot client는 자기 상태와 heartbeat를 Modbus에 write한다.
- command 중복 실행 방지는 `turtlebot_command_seq` / `turtlebot_command_ack_seq` 패턴을 사용한다.

## 7. 현재 열린 질문

1. 실제 TurtleBot 모델은 무엇인가? 예: TurtleBot3 Burger/Waffle Pi 등
2. ROS 2 distro와 TurtleBot 패키지 설치 상태는 어떤가?
3. 작업 공간 맵을 어디까지 포함할 것인가? 컨베이어 끝, 대기 위치, 배송 목표 위치 포함 여부
4. TurtleBot 배송 목표는 몇 개인가? 단일 목표인지, 작물/상자별 다중 목표인지
5. 컨베이어 끝에서 TurtleBot으로 실제 상차하는 물리 구조가 있는가, 아니면 시연에서는 도착/대기 이벤트로 대체할 것인가?
6. 압력센서 임계치 배송 호출은 MVP에 넣을 것인가, 후순위로 둘 것인가?
7. TurtleBot 상태를 Modbus로만 공유할지, ROS topic/WebSocket/DB 로그도 병행할지?

## 8. 다음 액션

1. TurtleBot 모델/ROS 2 distro/설치 패키지 확인
2. TurtleBot bringup 명령과 topic 목록 확인
3. teleop 또는 `/cmd_vel` 수동 주행 smoke test
4. SLAM mapping 실행 및 map 저장
5. Nav2 goal 1개 이동 테스트
6. Modbus TurtleBot heartbeat/status smoke client 작성
7. 테스트 결과를 이 문서와 진행 로그에 반영

## 9. 관련 문서

- `README.md`
- `docs/00_project/R&R_초안.md`
- `docs/30_plans/WBS_재검토_메모.md`
- `docs/20_subsystems/modbus/Modbus_Register_Map_확장_계획.md`
- `docs/40_logs/진행_로그.md`
- `docs/40_logs/작업_결정_메모.md`

## 10. 2026-06-25 Notion 기반 작업공간 구성 결과

### Notion에서 확인한 실행 순서

확인한 Notion 페이지:

- `SLAM` hub
- `터틀봇3 설치 가이드`
- `TurtleBot3 Waffle Pi`
- `Bringup TurtleBot3`
- `Gazebo Simulation`
- `SLAM`
- `SLAM Simulation`
- `Navigation`
- `Navigation Simulation`
- `Navigation 톺아보기`
- `관통 프로젝트`

핵심 절차:

1. TurtleBot SBC에서 `turtlebot3_bringup robot.launch.py` 실행
2. Remote PC에서 `/scan`, `/odom`, `/tf`, `/battery_state` topic 확인
3. Remote PC에서 Cartographer SLAM 실행
4. Teleop으로 미탐색 구역을 천천히 탐색
5. `nav2_map_server map_saver_cli`로 map 저장
6. 저장된 map으로 `turtlebot3_navigation2 navigation2.launch.py` 실행
7. RViz에서 `2D Pose Estimate` 후 `Nav2 Goal` 단일 이동 테스트
8. 관통 프로젝트용 `slam_pjt` package를 만들고 프로젝트 필요 node를 추가

### 실제 환경 확인 결과

- TurtleBot SBC: `turtlebot2@192.168.110.172`
- 모델: `TURTLEBOT3_MODEL=waffle_pi`
- Remote 확인 ROS: Humble
- 실제 TurtleBot SBC `ROS_DOMAIN_ID=32`
- Notion 예시 `ROS_DOMAIN_ID=30`과 달라, 이 작업공간 기본값은 실제 장비 기준 `32`로 둔다.
- Remote PC TurtleBot3 패키지 위치: `/home/ssafy/ros2/turtlebot3_ws/install/setup.bash`
- Remote PC에서 확인된 핵심 topic: `/scan`, `/odom`, `/imu`, `/battery_state`, `/cmd_vel`, `/tf`

### 생성한 작업공간

경로: `/home/ssafy/work/SmartFarmProject/workspaces/지웅/turtlebot`

생성/정리한 파일:

- `README.md`: 전체 실행 순서와 현재 환경 요약
- `docs/notion_turtlebot_sequence.md`: Notion TurtleBot 자료 요약
- `docs/runbook.md`: 실제 실행용 runbook
- `scripts/env.sh`: ROS/TurtleBot 공통 환경 로드, 기본 `ROS_DOMAIN_ID=32`
- `scripts/ssh_turtlebot.sh`: TurtleBot SBC SSH 접속 helper
- `scripts/check_topics.sh`: 핵심 topic 확인
- `scripts/start_slam_real.sh`: 실제 TurtleBot SLAM 실행
- `scripts/start_teleop.sh`: teleop 실행
- `scripts/save_map.sh`: map 저장
- `scripts/start_nav_real.sh`: 실제 TurtleBot Navigation2 실행
- `scripts/start_sim_world.sh`: Gazebo world 실행
- `scripts/start_slam_sim.sh`: Gazebo SLAM 실행
- `scripts/start_nav_sim.sh`: Gazebo Navigation 실행
- `config/waypoints.yaml`: `home`, `pickup_wait`, `delivery_goal` placeholder
- `ros2_ws/src/slam_pjt`: 관통 프로젝트용 ROS2 package
- `slam_pjt/turtlebot_modbus_heartbeat.py`: TurtleBot Modbus heartbeat/status smoke client

### 검증 결과

실행/검증한 명령:

```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/turtlebot
source scripts/env.sh
./scripts/check_topics.sh
/usr/bin/python3 -m py_compile ros2_ws/src/slam_pjt/slam_pjt/turtlebot_modbus_heartbeat.py
cd ros2_ws && colcon build --symlink-install --packages-select slam_pjt
ros2 run slam_pjt turtlebot_modbus_heartbeat --no-ros --once --dry-run
colcon test --packages-select slam_pjt
colcon test-result --verbose
```

검증 결과:

- `scripts/env.sh`: `TURTLEBOT3_MODEL=waffle_pi`, `ROS_DOMAIN_ID=32` 확인
- Remote PC에서 `/scan`, `/odom`, `/imu`, `/battery_state`, `/cmd_vel`, `/tf` topic 확인
- `slam_pjt` package build 성공
- `turtlebot_modbus_heartbeat --dry-run`이 `40055`, `40057`, `40058`, `40059`, `40063` write 계획을 출력
- package test 결과: `2 tests, 0 errors, 0 failures, 0 skipped`

### 다음 실제 장비 작업

1. `./scripts/start_slam_real.sh`로 Cartographer SLAM 실행
2. `./scripts/start_teleop.sh`로 천천히 공간 탐색
3. `./scripts/save_map.sh map/pjt_map_new`로 새 map 저장
4. `./scripts/start_nav_real.sh map/pjt_map_new.yaml`로 Navigation2 실행
5. RViz에서 `2D Pose Estimate` → `Nav2 Goal` 단일 이동 테스트
6. 성공한 waypoint를 `config/waypoints.yaml`에 실측 좌표로 반영
7. `turtlebot_modbus_heartbeat`를 dry-run에서 실제 Modbus server write로 전환

## 11. 2026-06-25 map 확인 및 Navigation2 1차 시도

### map 파일쌍 확인

`workspaces/지웅/turtlebot/map/`에는 다음 2개 파일이 있다.

- `pjt_map.yaml`
- `pjt_map.pgm`

`pjt_map.yaml` 내용 기준:

```yaml
image: pjt_map.pgm
mode: trinary
resolution: 0.05
origin: [-1.11, -3.59, 0]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.25
```

`pjt_map.yaml`이 같은 폴더의 `pjt_map.pgm`을 정상 참조하고 있으므로 Navigation2 map 입력으로 사용 가능하다.

### Navigation2 1차 시도 결과

실행:

```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/turtlebot
source scripts/env.sh
./scripts/start_nav_real.sh map/pjt_map.yaml
```

결과:

- 첫 실행은 ROS setup script와 `set -u` 충돌로 실패했다.
- `scripts/*.sh`의 `set -euo pipefail`을 `set -eo pipefail`로 수정했다.
- 재실행 후 Navigation2 stack은 실행됐지만, local costmap이 `base_link -> odom` TF를 기다리며 멈췄다.
- Remote PC에서 topic을 다시 확인하니 `/scan`, `/odom`, `/imu`, `/battery_state`, `/cmd_vel`, `/tf`가 보이지 않았다.
- SSH도 로그인 직후 원격 host가 닫는 상태였으므로, 현재는 TurtleBot SBC bringup 또는 ROS graph 연결이 끊긴 상태로 판단한다.

### 다음 실행 조건

Navigation2를 다시 실행하기 전에 아래가 먼저 OK여야 한다.

```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/turtlebot
source scripts/env.sh
./scripts/check_topics.sh
```

필수 OK topic:

- `/scan`
- `/odom`
- `/imu`
- `/battery_state`
- `/cmd_vel`
- `/tf`

TurtleBot 쪽 bringup은 SSH 종료와 분리하기 위해 `tmux` 사용을 권장한다.

```bash
ssh turtlebot2@192.168.110.172
tmux new -s bringup
export TURTLEBOT3_MODEL=waffle_pi
ros2 launch turtlebot3_bringup robot.launch.py
```

재접속:

```bash
tmux attach -t bringup
```

## 12. 2026-06-25 topic 복구 확인 및 Navigation2 재검증

### Remote PC topic 상태

사용자 확인 후 Remote PC에서 다시 확인한 결과 TurtleBot bringup topic은 정상 수신 중이다.

```text
OK: /scan
OK: /odom
OK: /imu
OK: /battery_state
OK: /cmd_vel
OK: /tf
```

추가 확인:

- `/odom`: 약 20Hz
- `/tf`: 약 33Hz
- `/scan`: 약 9.7Hz
- `tf2_echo odom base_link`: transform 수신 확인

### Navigation2 map 경로 이슈 수정

`workspaces/지웅/...`처럼 한글이 포함된 경로를 `nav2_map_server`가 잘못 처리해 다음 형태의 실패가 발생했다.

```text
Failed to load map yaml file: /home/ssafy/work/SmartFarmProject/workspaces/uC9C0uC6C5/turtlebot/map/pjt_map.yaml
```

수정:

- `scripts/start_nav_real.sh`에서 map 경로가 non-ASCII이면 `/tmp/smartfarm_turtlebot_nav_map/`으로 yaml/pgm을 복사한다.
- Navigation2에는 ASCII-safe mirror의 yaml 경로를 넘긴다.

수정 후 확인:

- `map_server`가 `/tmp/smartfarm_turtlebot_nav_map/pjt_map.yaml` 로드 성공
- `/map` topic 수신 확인
- map 크기: `67 x 95`, resolution `0.05`, origin `[-1.11, -3.59, 0]`
- `map_server`, `amcl`, `controller_server` active 확인

### 다음 수동 단계

현재 AMCL은 초기 자세 입력 전이므로 아래 경고가 뜨는 상태가 정상이다.

```text
AMCL cannot publish a pose or update the transform. Please set the initial pose...
```

다음 단계:

1. GUI가 있는 Remote PC 세션에서 Navigation2 실행
2. RViz에서 `2D Pose Estimate`로 실제 TurtleBot 위치/방향 지정
3. scan이 map 벽/장애물과 겹치는지 확인
4. 안전 확보 후 가까운 지점으로 `Nav2 Goal` 단일 이동 테스트
5. 성공 좌표를 `config/waypoints.yaml`에 반영

### background watch 알림 정리

이전 Navigation2 background 실행의 watch pattern이 `Timed out waiting for transform` 로그를 반복 알림으로 보냈다. 중복 Nav2 process를 정리하고 clean launch를 다시 실행했다.

현재 clean launch 확인값:

- `/map` publisher: 1
- `map_server`: active
- `amcl`: active
- `controller_server`: active
- `/map`: `67 x 95`, resolution `0.05`, origin `[-1.11, -3.59, 0]`

남은 transform 대기는 RViz에서 `2D Pose Estimate`를 넣기 전의 AMCL 초기 자세 미지정 상태로 보고, 초기 자세 입력 후 scan-map 정합을 확인한다.

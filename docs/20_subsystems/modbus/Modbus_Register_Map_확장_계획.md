# Modbus Register Map 확장 계획

작성일: 2026-06-24  
대상 server: `192.168.110.109:50200`  
관리 workspace: `/home/ssafy/work/SmartFarmProject/workspaces/지웅/modbus`

## 1. 계획 목적

기존 컨베이어 block `40021~40030`은 유지하면서, Modbus server가 관리할 데이터를 다음 범위까지 확장한다.

1. 농장 현황
   - 총 수확량
   - AI 불량 검출률
   - TurtleBot 누적 배송
   - 작물별 양품/불량품 수량: 토마토, 당근, 무
2. Dobot 상황
3. TurtleBot 상황
4. Web에서 내리는 상위 명령
   - `수확시작`
   - `전체 시스템 일시 정지`

이 계획은 승인되어 `workspaces/지웅/modbus/register_map.py`와 `tests/test_register_map.py`에 1차 반영했다. 실제 장치 client 연동 전까지는 register map 기준 문서로 사용한다.

## 2. 설계 원칙

- Modbus holding register는 16-bit 정수이므로 누적 count는 32-bit pair로 저장한다.
  - 예: `*_lo`, `*_hi`
  - 값 계산: `value = hi * 65536 + lo`
- rate는 float 대신 정수 scale로 저장한다.
  - AI 불량 검출률: basis point 사용, `0~10000 = 0.00%~100.00%`
  - 예: `1234 = 12.34%`
- 명령 register는 반복 실행 방지를 위해 `command_seq` / `ack_seq`를 같이 둔다.
  - Web/backend가 command를 쓰고 `command_seq`를 1 증가
  - 실행 주체가 처리 후 `ack_seq = command_seq`로 갱신
  - 이렇게 해야 같은 명령 값이 계속 남아 있어도 중복 실행을 막을 수 있다.
- 각 장치의 실제 상태는 해당 장치 client가 write한다.
  - Dobot 상태: Dobot/ROS2 client가 write
  - TurtleBot 상태: TurtleBot/ROS2 client가 write
  - 농장 통계: backend/orchestrator 또는 통계 aggregator가 write
- Web은 직접 장치 세부 register를 건드리기보다 `system_command` 중심으로 명령한다.

## 3. 전체 block 제안

| Block | Registers | 목적 | 주 write 주체 |
|---|---:|---|---|
| Conveyor | `40021~40030` | 기존 컨베이어 명령/상태/비전 이벤트 | PC vision, Raspberry Pi conveyor client |
| Dobot | `40031~40050` | Dobot 명령/상태/작업 단계/heartbeat | Web/backend 명령, Dobot client 상태 |
| TurtleBot | `40051~40070` | TurtleBot 명령/상태/배송/배터리/heartbeat | Web/backend 명령, TurtleBot client 상태 |
| Farm/System | `40071~40100` | 상위 시스템 명령, 농장 통계, 전체 상태 | Web/backend, 통계 aggregator |

## 4. Web 상위 명령 설계

Web에서 직접 내릴 명령은 우선 두 개로 제한한다.

| 값 | 명령 | 의미 |
|---:|---|---|
| 0 | none | 대기/명령 없음 |
| 1 | harvest_start | 수확시작 |
| 2 | pause_all | 전체 시스템 일시 정지 |
| 3 | resume_all 후보 | 일시정지 해제가 필요해질 경우 추가 후보 |

> 현재 사용자가 명시한 명령은 `수확시작`, `전체 시스템 일시 정지` 두 개다. 다만 일시정지는 보통 해제 동작이 필요하므로, 구현 전 `resume_all`을 별도 명령으로 둘지, `수확시작`이 resume 역할까지 겸할지 결정해야 한다.

## 5. Farm/System block 초안: `40071~40100`

| Register | Address | Name | Owner | 설명 |
|---:|---:|---|---|---|
| 40071 | 70 | `system_command` | Web/backend | 0 none, 1 harvest_start, 2 pause_all, 3 resume_all 후보 |
| 40072 | 71 | `system_command_seq` | Web/backend | command 중복 실행 방지용 증가 번호 |
| 40073 | 72 | `system_command_ack_seq` | Orchestrator/backend | 마지막 처리 완료 command_seq |
| 40074 | 73 | `system_state` | Orchestrator/backend | 0 idle, 1 harvesting, 2 paused, 3 error, 4 emergency_stop 후보 |
| 40075 | 74 | `system_error_code` | Orchestrator/backend | 전체 시스템 에러 코드 |
| 40076 | 75 | `ai_defect_rate_bp` | AI/backend | AI 불량 검출률, 0~10000 = 0.00~100.00% |
| 40077 | 76 | `total_harvest_count_lo` | backend/stat aggregator | 총 수확량 32-bit low |
| 40078 | 77 | `total_harvest_count_hi` | backend/stat aggregator | 총 수확량 32-bit high |
| 40079 | 78 | `turtlebot_delivery_total_lo` | backend/TurtleBot aggregator | TurtleBot 누적 배송 32-bit low |
| 40080 | 79 | `turtlebot_delivery_total_hi` | backend/TurtleBot aggregator | TurtleBot 누적 배송 32-bit high |
| 40081 | 80 | `tomato_good_count_lo` | backend/stat aggregator | 토마토 양품 32-bit low |
| 40082 | 81 | `tomato_good_count_hi` | backend/stat aggregator | 토마토 양품 32-bit high |
| 40083 | 82 | `tomato_bad_count_lo` | backend/stat aggregator | 토마토 불량품 32-bit low |
| 40084 | 83 | `tomato_bad_count_hi` | backend/stat aggregator | 토마토 불량품 32-bit high |
| 40085 | 84 | `carrot_good_count_lo` | backend/stat aggregator | 당근 양품 32-bit low |
| 40086 | 85 | `carrot_good_count_hi` | backend/stat aggregator | 당근 양품 32-bit high |
| 40087 | 86 | `carrot_bad_count_lo` | backend/stat aggregator | 당근 불량품 32-bit low |
| 40088 | 87 | `carrot_bad_count_hi` | backend/stat aggregator | 당근 불량품 32-bit high |
| 40089 | 88 | `radish_good_count_lo` | backend/stat aggregator | 무 양품 32-bit low |
| 40090 | 89 | `radish_good_count_hi` | backend/stat aggregator | 무 양품 32-bit high |
| 40091 | 90 | `radish_bad_count_lo` | backend/stat aggregator | 무 불량품 32-bit low |
| 40092 | 91 | `radish_bad_count_hi` | backend/stat aggregator | 무 불량품 32-bit high |
| 40093 | 92 | `farm_stats_seq` | backend/stat aggregator | 통계 갱신 sequence |
| 40094 | 93 | `farm_heartbeat` | backend/stat aggregator | 통계 갱신 주체 heartbeat |
| 40095~40100 | 94~99 | reserved | reserved | 확장 예비 |

## 6. Dobot block 초안: `40031~40050`

| Register | Address | Name | Owner | 설명 |
|---:|---:|---|---|---|
| 40031 | 30 | `dobot_command` | Orchestrator/backend | 0 none, 1 home, 2 move_capture_pose, 3 pick, 4 place, 5 stop, 6 reset 후보 |
| 40032 | 31 | `dobot_target_slot` | Orchestrator/backend | 수확/이동 대상 slot 또는 위치 index |
| 40033 | 32 | `dobot_command_seq` | Orchestrator/backend | Dobot command sequence |
| 40034 | 33 | `dobot_command_ack_seq` | Dobot client | 마지막 처리 완료 command_seq |
| 40035 | 34 | `dobot_status` | Dobot client | 0 idle, 1 moving, 2 capturing, 3 picking, 4 placing, 5 paused, 6 error 후보 |
| 40036 | 35 | `dobot_error_code` | Dobot client | Dobot/ROS2 error code |
| 40037 | 36 | `dobot_current_step` | Dobot client | 현재 sequence step |
| 40038 | 37 | `dobot_quality_result` | Dobot/AI client | 0 unknown, 1 good, 2 bad 후보 |
| 40039 | 38 | `dobot_busy` | Dobot client | 0/1 |
| 40040 | 39 | `dobot_heartbeat` | Dobot client | 증가 heartbeat |
| 40041 | 40 | `dobot_last_event` | Dobot client | 마지막 event enum |
| 40042~40050 | 41~49 | reserved | reserved | Dobot 확장 예비 |

Dobot에 Web이 직접 세부 명령을 내리는 구조는 MVP에서는 권장하지 않는다. Web은 `system_command=harvest_start/pause_all`만 쓰고, backend/orchestrator가 Dobot block에 필요한 세부 command를 쓰는 편이 안전하다.

## 7. TurtleBot block 초안: `40051~40070`

| Register | Address | Name | Owner | 설명 |
|---:|---:|---|---|---|
| 40051 | 50 | `turtlebot_command` | Orchestrator/backend | 0 none, 1 deliver_start, 2 pause, 3 resume, 4 return_home, 5 stop, 6 reset 후보 |
| 40052 | 51 | `turtlebot_target_goal` | Orchestrator/backend | 배송 목적지/goal index |
| 40053 | 52 | `turtlebot_command_seq` | Orchestrator/backend | TurtleBot command sequence |
| 40054 | 53 | `turtlebot_command_ack_seq` | TurtleBot client | 마지막 처리 완료 command_seq |
| 40055 | 54 | `turtlebot_status` | TurtleBot client | 0 idle, 1 navigating, 2 arrived, 3 delivering, 4 paused, 5 error 후보 |
| 40056 | 55 | `turtlebot_error_code` | TurtleBot client | navigation/ROS2 error code |
| 40057 | 56 | `turtlebot_nav_state` | TurtleBot client | nav2 등 내부 navigation state |
| 40058 | 57 | `turtlebot_battery_percent` | TurtleBot client | 0~100 |
| 40059 | 58 | `turtlebot_current_goal` | TurtleBot client | 현재 goal index |
| 40060 | 59 | `turtlebot_delivery_count_lo` | TurtleBot client | TurtleBot 자체 누적 배송 32-bit low |
| 40061 | 60 | `turtlebot_delivery_count_hi` | TurtleBot client | TurtleBot 자체 누적 배송 32-bit high |
| 40062 | 61 | `turtlebot_last_event` | TurtleBot client | 마지막 event enum |
| 40063 | 62 | `turtlebot_heartbeat` | TurtleBot client | 증가 heartbeat |
| 40064~40070 | 63~69 | reserved | reserved | TurtleBot 확장 예비 |

Farm/System block의 `turtlebot_delivery_total`은 dashboard용 전체 통계이고, TurtleBot block의 `turtlebot_delivery_count`는 TurtleBot client가 직접 보고하는 원천값으로 둔다. 둘 중 하나를 원천으로 정하면 다른 하나는 backend가 복사/집계한다.

## 8. 수확시작 flow 초안

1. Web/backend가 `system_command=1`, `system_command_seq += 1` write.
2. Orchestrator가 새 command_seq를 읽고 `system_state=harvesting`으로 변경.
3. Orchestrator가 필요한 경우 Dobot block에 `dobot_command`를 write.
4. Dobot client가 작업 진행 중 `dobot_status/current_step/busy/heartbeat` 갱신.
5. AI/backend가 결과를 받아 crop별 good/bad count와 `ai_defect_rate_bp` 갱신.
6. TurtleBot 배송이 필요하면 Orchestrator가 TurtleBot block에 `turtlebot_command=deliver_start` write.
7. TurtleBot client가 `turtlebot_status`, `current_goal`, `delivery_count`, `heartbeat` 갱신.
8. Orchestrator가 처리 완료 후 `system_command_ack_seq = system_command_seq` write.

## 9. 전체 시스템 일시 정지 flow 초안

1. Web/backend가 `system_command=2`, `system_command_seq += 1` write.
2. Orchestrator가 `system_state=paused`로 변경.
3. Orchestrator가 장치별 pause/stop 성격의 명령을 전파한다.
   - Conveyor: 기존 command에 stop 또는 emergency_stop 성격 적용 여부 결정 필요
   - Dobot: `dobot_command=stop/pause 후보`
   - TurtleBot: `turtlebot_command=pause 후보`
4. 각 장치 client가 자신의 실제 status를 갱신한다.
5. Orchestrator가 `system_command_ack_seq = system_command_seq` write.

## 10. 아직 결정해야 할 질문

1. `전체 시스템 일시 정지` 이후 해제 명령을 따로 둘지?
   - 후보 A: `resume_all=3` 추가
   - 후보 B: `수확시작=1`이 pause 해제와 재시작을 겸함
2. `pause_all`에서 컨베이어는 `stop`으로 둘지, `emergency_stop`으로 둘지?
   - 일반 일시정지면 `stop`
   - 안전 비상정지면 `emergency_stop`
3. 농장 통계의 원천은 누구로 둘지?
   - backend/stat aggregator 권장
   - AI/Dobot/TurtleBot client가 각각 일부를 직접 쓰게 할 수도 있으나 race condition 위험 증가
4. 작물 구분 enum을 별도로 둘지?
   - 현재는 토마토/당근/무 count를 고정 register로 분리
   - 작물이 늘어날 예정이면 crop_id + dynamic counter 방식 검토 필요
5. AI 불량 검출률은 전체 누적 기준인지, 최근 N개/오늘 기준인지?
   - dashboard에 필요한 기준을 먼저 정해야 함

## 11. 구현 반영 순서 제안

1. 이 register map 초안 승인
2. `workspaces/지웅/modbus/register_map.py`에 Farm/System, Dobot, TurtleBot 상세 register 반영
3. `tests/test_register_map.py`에 주소/32-bit pair/rate scale 테스트 추가
4. `modbus_client_smoke.py`에 system command write/read 옵션 추가
5. backend/web command client는 `system_command + system_command_seq`만 write하도록 구현
6. Dobot/TurtleBot client는 각자 상태 register만 우선 write하는 heartbeat smoke부터 구현


## 12. 2026-06-24 코드 반영 결과

반영 파일:
- `/home/ssafy/work/SmartFarmProject/workspaces/지웅/modbus/register_map.py`
- `/home/ssafy/work/SmartFarmProject/workspaces/지웅/modbus/tests/test_register_map.py`
- `/home/ssafy/work/SmartFarmProject/workspaces/지웅/modbus/modbus_client_smoke.py`

반영 내용:
- Web 상위 명령: `system_command` = 0 none, 1 harvest_start, 2 pause_all, 3 resume_all
- 중복 실행 방지: `system_command_seq`, `system_command_ack_seq`
- Dobot command/status block: `40031~40050`
- TurtleBot command/status/delivery block: `40051~40070`
- Farm/System 통계 block: `40071~40100`
- 32-bit 누적 count helper: `split_u32()`, `combine_u32()`
- `modbus_client_smoke.py --system-command harvest_start --system-command-seq N` smoke 옵션 추가

주의:
- 다른 세션에서 Modbus server를 건드릴 수 있어 이번 작업에서는 실행 중인 50200 서버를 재시작/종료하지 않았다.
- 검증은 별도 포트 `127.0.0.1:50201` 임시 서버로 수행한다.

## 13. 검증 결과

검증 명령:
```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/modbus
source .venv/bin/activate
python -m py_compile register_map.py modbus_server.py modbus_client_smoke.py tests/test_register_map.py
PYTHONPATH=. python tests/test_register_map.py  # 함수 직접 호출 방식
python modbus_server.py --host 127.0.0.1 --port 50201 --print-register-map
python modbus_client_smoke.py --host 127.0.0.1 --port 50201 --write-demo --system-command harvest_start --system-command-seq 7
```

실제 smoke 결과:
```text
READ OK 127.0.0.1:50201 count=80 first10=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
WRITE DEMO OK 40021/40022=[0, 0]
SYSTEM COMMAND OK 40071/40072=[1, 7] command=harvest_start
```

다른 세션과 충돌을 피하기 위해 기본 endpoint `192.168.110.109:50200` 서버는 재시작하지 않았고, 임시 검증 서버 `127.0.0.1:50201`은 검증 후 종료했다.

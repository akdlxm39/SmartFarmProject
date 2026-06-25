# SmartFarmProject Modbus Server 작업 메모

작성일: 2026-06-24  
관리 경로: `/home/ssafy/work/SmartFarmProject/workspaces/지웅/modbus`  
server endpoint: `192.168.110.109:50200`

## 1. 범위
이 문서는 SmartFarmProject의 **공통 Modbus TCP server / shared register layer**를 관리한다.

이제 Modbus server는 컨베이어 전용이 아니라, 추후 Dobot 상태, TurtleBot 상태, 농장/시스템 상태까지 함께 관리하는 공통 상태/제어 레이어로 확장한다.

### 직접 다룰 것
- Modbus server 실행 위치와 endpoint
- shared holding register map
- register block별 write ownership
- `pymodbus==3.13.1` 기준 server/client smoke test
- PC vision, Raspberry Pi, Dobot, TurtleBot, backend/dashboard가 붙는 방식

### 인터페이스 수준에서만 언급할 것
- 컨베이어 GPIO motor 세부 구현
- Dobot ROS2 motion 세부 구현
- TurtleBot navigation 세부 구현
- Django/Vue 화면 구현

## 2. 현재 확정 구조
- Modbus server workspace: `workspaces/지웅/modbus`
- Modbus server endpoint: `192.168.110.109:50200`
- 기준 라이브러리: `pymodbus==3.13.1`
- 현재 PC가 `192.168.110.109/24` 주소를 가진다.
- Raspberry Pi 5(`ssafy@192.168.110.139`)는 server가 아니라 **Modbus client + conveyor GPIO controller**다.
- PC/ROS2 vision node도 Modbus client다.
- future Dobot client와 TurtleBot client도 같은 server에 붙어 각자 상태 block을 갱신한다.

## 3. 작업공간 구조
```text
workspaces/지웅/modbus/
  README.md
  requirements.txt
  register_map.py
  modbus_server.py
  modbus_client_smoke.py
  tests/test_register_map.py
  references/
    server_test.py
    server_test2.py
    client_test.py
    requirements.txt
```

`references/`에는 기존 컨베이어/RealSense 쪽에 흩어져 있던 pymodbus server/client 예제를 가져와 보관했다. 실제 기준 register map과 server 실행은 `register_map.py`, `modbus_server.py`를 따른다.

## 4. Register block 계획
| Block | Registers | Owner / 용도 |
|---|---:|---|
| Conveyor | `40021~40030` | PC vision/manual client, Raspberry Pi conveyor client |
| Dobot future | `40031~40050` | future Dobot ROS2 client 상태/이벤트 |
| TurtleBot future | `40051~40070` | future TurtleBot navigation client 상태/이벤트 |
| System/Farm future | `40071~40100` | backend/system mode, heartbeat, farm status |

## 5. Conveyor block ownership
| Register | Address | Name | 주 쓰기 주체 | 주 읽기 주체 |
|---:|---:|---|---|---|
| 40021 | 20 | `conveyor_command` | PC vision/manual client | Raspberry Pi |
| 40022 | 21 | `conveyor_speed_cmd` | PC vision/manual client | Raspberry Pi |
| 40023 | 22 | `conveyor_status` | Raspberry Pi | PC/dashboard |
| 40024 | 23 | `conveyor_error_code` | Raspberry Pi | PC/dashboard |
| 40025 | 24 | `cube_detected` | PC vision | Pi/dashboard |
| 40026 | 25 | `cube_color` | PC vision | Pi/dashboard |
| 40027 | 26 | `last_vision_event` | PC vision | Pi/dashboard |
| 40028~40030 | 27~29 | reserved | reserved | reserved |

## 6. Future Dobot block 초안
| Register | Address | Name | 주 쓰기 주체 | 비고 |
|---:|---:|---|---|---|
| 40031 | 30 | `dobot_status` | future Dobot client | idle/moving/gripping/placing/error 후보 |
| 40032 | 31 | `dobot_error_code` | future Dobot client | ROS/Dobot error |
| 40033 | 32 | `dobot_current_step` | future Dobot client | harvest/capture/place sequence step |
| 40034 | 33 | `dobot_target_slot` | future Dobot/manual client | target index |
| 40035 | 34 | `dobot_quality_result` | future vision/Dobot client | unknown/normal/defect 후보 |
| 40036 | 35 | `dobot_last_event` | future Dobot client | last event enum |
| 40037 | 36 | `dobot_busy` | future Dobot client | 0/1 |
| 40038 | 37 | `dobot_heartbeat` | future Dobot client | incrementing heartbeat |
| 40039~40050 | 38~49 | reserved | reserved | 확장 예비 |

## 7. Future TurtleBot block 초안
| Register | Address | Name | 주 쓰기 주체 | 비고 |
|---:|---:|---|---|---|
| 40051 | 50 | `turtlebot_status` | future TurtleBot client | idle/navigating/arrived/error 후보 |
| 40052 | 51 | `turtlebot_error_code` | future TurtleBot client | nav/ROS error |
| 40053 | 52 | `turtlebot_nav_state` | future TurtleBot client | navigation state |
| 40054 | 53 | `turtlebot_current_goal` | future backend/TurtleBot client | goal index |
| 40055 | 54 | `turtlebot_battery_percent` | future TurtleBot client | 0~100 |
| 40056 | 55 | `turtlebot_last_event` | future TurtleBot client | last event enum |
| 40057 | 56 | `turtlebot_heartbeat` | future TurtleBot client | incrementing heartbeat |
| 40058~40070 | 57~69 | reserved | reserved | 확장 예비 |

## 8. 주소 변환 기준
- 문서 표기는 `40021` 같은 holding register 번호를 사용한다.
- `pymodbus` protocol address는 기본 zero-based 기준이다.
- 예: `40021 -> 20`, `40031 -> 30`, `40051 -> 50`.
- 실제 client/server 코드는 이 변환을 `register_map.py`에서 관리한다.

## 9. 실행/검증
환경 준비:
```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/modbus
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
```

server 실행:
```bash
python modbus_server.py --host 192.168.110.109 --port 50200 --print-register-map
```

smoke test:
```bash
python modbus_client_smoke.py --host 192.168.110.109 --port 50200 --write-demo
```

## 10. 안전 규칙
1. register별 write ownership을 유지한다.
2. PC/manual client는 Pi가 실제 모터 상태 기준으로 쓰는 `40023/40024`를 덮어쓰지 않는다.
3. Dobot/TurtleBot block은 실제 client가 붙기 전까지 future/reserved로 취급한다.
4. backend/dashboard는 MVP에서는 read 중심으로 붙인다.
5. 비밀번호는 문서/코드에 저장하지 않는다.

## 11. 2026-06-24 로컬 서버 검증 결과
현재 PC가 `192.168.110.109/24`를 가지고 있음을 `ip -4 addr`로 확인했다.

검증한 명령:
```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/modbus
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
python -m py_compile register_map.py modbus_server.py modbus_client_smoke.py tests/test_register_map.py
PYTHONPATH=. python tests/test_register_map.py  # 함수 직접 호출 방식으로 검증
python modbus_server.py --host 192.168.110.109 --port 50200 --print-register-map
python modbus_client_smoke.py --host 192.168.110.109 --port 50200 --write-demo
```

실제 smoke 결과:
```text
READ OK 192.168.110.109:50200 count=80 first10=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
WRITE DEMO OK 40021/40022=[0, 0]
```

기존 컨베이어 client도 새 endpoint로 명령 write가 성공했다.
```text
command=0(stop) speed=0 target=192.168.110.109:50200 ok=True
```

현재 Hermes background process에서 server가 실행 중이다: `proc_97a93c7ffdc8`.

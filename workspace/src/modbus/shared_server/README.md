# SmartFarmProject Modbus Server Workspace

이 폴더는 SmartFarmProject의 **Modbus TCP server / shared register layer**를 관리하는 중앙 작업공간이다.

- workspace: `/home/ssafy/work/SmartFarmProject/workspace/src/modbus/shared_server`
- server endpoint: `192.168.110.109:50200`
- Python Modbus: `pymodbus==3.13.1`
- 역할: 컨베이어, 추후 Dobot, TurtleBot, 농장 상태를 함께 담는 shared holding-register layer

## 역할 분리

| 구성요소 | 역할 |
|---|---|
| Modbus server `192.168.110.109:50200` | holding register 상태 유지 |
| PC/ROS2 vision client | 컨베이어 명령/비전 상태 write: `40021/40022/40025~40027` |
| Raspberry Pi conveyor client | 컨베이어 실제 모터 제어, 실제 상태 write: `40023/40024` |
| future Dobot client | Dobot 상태/이벤트 write: `40031~40050` |
| future TurtleBot client | TurtleBot 상태/이벤트 write: `40051~40070` |
| backend/dashboard | 가능하면 read 중심, 필요 시 별도 command register만 write |

## Register block 초안

| Block | Registers | 용도 |
|---|---:|---|
| Conveyor | `40021~40030` | 컨베이어 command/status/vision event |
| Dobot future | `40031~40050` | Dobot 상태, error, 현재 step, busy, heartbeat |
| TurtleBot future | `40051~40070` | TurtleBot 주행 상태, goal, battery, heartbeat |
| System/Farm future | `40071~40100` | 전체 시스템 mode/heartbeat/farm status |

상세 register map은 `register_map.py`의 `REGISTER_SPECS`를 기준으로 한다.

## 환경 준비

```bash
cd /home/ssafy/work/SmartFarmProject/workspace/src/modbus/shared_server
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
```

## 서버 실행

현재 PC가 `192.168.110.109/24` 주소를 가지고 있으므로 기본값 그대로 실행한다.

```bash
cd /home/ssafy/work/SmartFarmProject/workspace/src/modbus/shared_server
source .venv/bin/activate
python modbus_server.py --host 192.168.110.109 --port 50200 --print-register-map
```

다른 인터페이스까지 모두 받을 필요가 있으면 `--host 0.0.0.0`으로 실행한다.

## smoke test

다른 터미널에서:

```bash
cd /home/ssafy/work/SmartFarmProject/workspace/src/modbus/shared_server
source .venv/bin/activate
python modbus_client_smoke.py --host 192.168.110.109 --port 50200 --write-demo
```

성공 예시는 다음과 같다.

```text
READ OK 192.168.110.109:50200 count=80 first10=[0, 0, ...]
WRITE DEMO OK 40021/40022=[0, 0]
```

## 가져온 기존 Modbus 자료

기존 컨베이어/RealSense 쪽에 흩어져 있던 pymodbus 예제는 아래에 참고용으로 복사했다.

- `references/server_test.py`
- `references/server_test2.py`
- `references/client_test.py`
- `references/requirements.txt`

기존 운영 코드와 register ownership은 아래 작업물에서 온 내용을 통합했다.

- `workspace/src/realsense/realsense/conveyor_modbus.py`
- `workspace/src/conveyor/modbus_client/register_map.py`
- `workspace/src/conveyor/modbus_client/conveyor_modbus_client_controller.py`

## 안전 규칙

1. PC/manual client는 Pi가 소유하는 `40023/40024`를 쓰지 않는다.
2. Raspberry Pi local emergency latch가 켜져 있으면 run command가 있어도 모터를 돌리지 않는다.
3. Dobot/TurtleBot register는 아직 future block이며, 실제 client가 생기기 전까지 server는 값을 보관만 한다.
4. dashboard/backend는 MVP에서는 read 중심으로 붙인다.
5. 장치 비밀번호는 문서나 코드에 저장하지 않는다.

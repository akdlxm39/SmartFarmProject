# Conveyor Modbus Async + Raspberry Pi 전환 Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** `pymodbus==3.13.1` 기반 비동기 Modbus 구조로 전환해, D435i/OpenCV 비전 루프가 Modbus read/write 때문에 버벅이지 않게 하고, Raspberry Pi 5가 외부 Modbus TCP server(`192.168.110.109:50200`)의 client로 동작하면서 컨베이어 모터 GPIO 제어를 안정적으로 담당하게 한다.

**Architecture:** PC/ROS2 쪽 `topview_color_detector`는 D435i frame 처리와 색상 ROI 감지만 담당하고, Modbus write는 `AsyncModbusTcpClient`를 쓰는 별도 async worker/queue로 분리한다. Modbus TCP server는 별도 장비/프로세스 `192.168.110.109:50200`으로 유지한다. Raspberry Pi 5/Raspbian(`ssafy@192.168.110.139`)은 **Modbus client**로 server의 holding register `40021~40030`을 async polling/write하고, register command에 따라 GPIO `DIR/STEP/ENABLE`로 컨베이어를 제어한다. Dashboard/다른 client는 가능하면 read 중심으로 붙이고, 쓰기 주체를 최소화한다.

**Tech Stack:** ROS 2 Humble, Python 3.10, D435i RealSense color topic, OpenCV/HSV ROI detection, `pymodbus==3.13.1`, `asyncio`, Raspberry Pi 5 Raspbian, `gpiod`, Modbus TCP server `192.168.110.109:50200`, Raspberry Pi SSH target `ssafy@192.168.110.139`, holding registers `40021~40030` / pymodbus protocol addresses `20~29`.

---

## 0. 참고한 현재 자료

- 사용자 제공 기준: `pymodbus==3.9.2` 동기 방식으로 client read/write 시 버벅임 발생 → `pymodbus==3.13.1` 필요
- 사용자 제공 기준: Modbus server는 `192.168.110.109:50200`, Raspberry Pi 5/Raspbian은 `ssafy@192.168.110.139`이며, 컨베이어 모터 제어는 Raspberry Pi에서 수행
- 참고 코드:
  - `workspaces/지웅/conveyor/ref/realsense/server_test.py`
  - `workspaces/지웅/conveyor/ref/realsense/server_test2.py`
  - `workspaces/지웅/conveyor/ref/realsense/client_test.py`
  - `workspaces/지웅/conveyor/ref/conveyor/conveyor_test.py`
- 현재 ROS2 테스트 패키지:
  - `workspaces/지웅/ros2_ws/src/conveyor_vision_test`
- 현재 컨베이어 register block:
  - human notation: `40021~40030`
  - pymodbus zero-based protocol address: `20~29`

## 1. 핵심 변경 결정

### 1.1 기존 문제

현재 `topview_color_detector`는 ROS image callback 내부에서 감지 결과를 만든 뒤, 동기식 `ModbusTcpClient.write_registers()` 계열 호출을 수행한다. Modbus TCP 연결/쓰기/읽기가 느려지면 image callback이 막히고, 결과적으로 OpenCV 표시와 ROS frame 처리가 버벅일 수 있다.

### 1.2 새 구조

```text
PC / ROS2 / D435i
  └─ topview_color_detector
      ├─ image callback: top-view + ROI + HSV detection only
      ├─ state machine: latest ConveyorRegisterState 생성
      └─ async Modbus writer: latest state만 queue에 넣고 즉시 callback 반환
             │
             │ AsyncModbusTcpClient, pymodbus==3.13.1
             ▼
External Modbus TCP server
  └─ 192.168.110.109:50200
      └─ holding registers 20~29 유지

Raspberry Pi 5 / Raspbian
  └─ ssafy@192.168.110.139 / conveyor_pi_controller
      ├─ AsyncModbusTcpClient로 server 접속
      ├─ motor control loop: 40021/40022 polling 후 GPIO 제어
      └─ status loop: 40023/40024를 실제 모터 상태 기준으로 write
```

### 1.3 register ownership

| Register | Protocol address | Name | 주 쓰기 주체 | 주 읽기 주체 | 비고 |
|---:|---:|---|---|---|---|
| 40021 | 20 | `conveyor_command` | PC vision 또는 수동 client | Raspberry Pi Modbus client motor loop | `0 stop`, `1 run_clockwise`, `2 run_counter_clockwise`, `3 reset`, `4 emergency_stop` |
| 40022 | 21 | `conveyor_speed_cmd` | PC vision 또는 수동 client | Raspberry Pi Modbus client motor loop | MVP에서는 step delay/속도 preset으로 해석 |
| 40023 | 22 | `conveyor_status` | Raspberry Pi | PC/dashboard | `0 idle`, `1 running`, `2 delivered`, `3 error`, `4 emergency_stopped` |
| 40024 | 23 | `conveyor_error_code` | Raspberry Pi | PC/dashboard | GPIO/command/Modbus connection error |
| 40025 | 24 | `cube_detected` | PC vision | Raspberry Pi/dashboard | `0/1` |
| 40026 | 25 | `cube_color` | PC vision | Raspberry Pi/dashboard | `0 none`, `1 red`, `2 green`, `3 unknown` |
| 40027 | 26 | `last_vision_event` | PC vision | Raspberry Pi/dashboard | `0 none`, `1 cube_detected`, `2 cube_lost`, `3 delivered`, `4 error`, `5 emergency_stop` |
| 40028 | 27 | `reserved_conveyor_1` | reserved | reserved | 추후 heartbeat/sequence 후보 |
| 40029 | 28 | `reserved_conveyor_2` | reserved | reserved | 추후 Pi uptime/status 후보 |
| 40030 | 29 | `reserved_conveyor_3` | reserved | reserved | 추후 확장 |

> 주의: 40023/40024는 Raspberry Pi가 실제 모터 상태 기준으로 갱신한다. PC 비전 노드는 기존처럼 전체 40021~40027을 항상 덮어쓰는 방식에서 벗어나야 한다. 그렇지 않으면 Pi가 쓴 status/error를 PC가 다시 덮어써 race condition이 생긴다.

---

## 2. 단계별 구현 계획

### Task 1: 의존성 버전 전환 기준 문서화

**Objective:** PC/ROS와 Raspberry Pi 모두 `pymodbus==3.13.1`을 기준으로 맞춘다.

**Files:**
- Modify: `README.md`
- Modify: `docs/Conveyor_ROI_Modbus_구현_계획.md`
- Modify: `workspaces/지웅/conveyor/requirements.txt`
- Create: `workspaces/지웅/conveyor/pi_controller/requirements.txt`

**Steps:**
1. 기존 문서의 `pymodbus==3.9.2` 문구를 `pymodbus==3.13.1`로 바꾼다.
2. `workspaces/지웅/conveyor/requirements.txt`에 PC 도구용 `pymodbus==3.13.1`을 추가한다.
3. Pi controller 전용 `requirements.txt`를 만든다.

**Pi controller requirements 초안:**
```text
pymodbus==3.13.1
```

`gpiod`는 Raspbian에서 pip보다 apt/system package로 설치되는 경우가 많으므로 requirements에 무리하게 고정하지 않고 README에 별도 설치/확인으로 둔다.

**Verification:**
```bash
python3 - <<'PY'
import pymodbus
print(pymodbus.__version__)
PY
```
Expected: `3.13.1`

---

### Task 2: pymodbus 3.13.1 API 차이 반영

**Objective:** 기존 `slave=`/`unit=` 호환 호출을 3.13.1 기준 `device_id=` 호출로 전환한다.

**Files:**
- Modify: `workspaces/지웅/ros2_ws/src/conveyor_vision_test/conveyor_vision_test/conveyor_modbus.py`
- Modify/Test: `workspaces/지웅/ros2_ws/src/conveyor_vision_test/test/test_topview_color_detector.py`

**Confirmed API:**
```python
from pymodbus.client import AsyncModbusTcpClient

await client.write_registers(address, values, device_id=1)
await client.read_holding_registers(address, count=10, device_id=1)
```

실제 `pymodbus==3.13.1` 임시 venv 검증 결과:
```text
AsyncModbusTcpClient.write_registers(self, address, values, *, device_id=1, no_response_expected=False)
AsyncModbusTcpClient.read_holding_registers(self, address, *, count=1, device_id=1, no_response_expected=False)
```

**Verification:**
- fake async client로 `device_id` 인자가 전달되는지 단위 테스트한다.
- 기존 register 주소 변환 테스트는 유지한다: `40021 -> 20`, `40030 -> 29`.

---

### Task 3: PC/ROS 비전 노드에서 Modbus write를 callback 밖 async worker로 분리

**Objective:** 이미지 callback은 Modbus 네트워크 I/O를 기다리지 않고 즉시 반환하게 만든다.

**Files:**
- Create: `workspaces/지웅/ros2_ws/src/conveyor_vision_test/conveyor_vision_test/async_modbus_client.py`
- Modify: `workspaces/지웅/ros2_ws/src/conveyor_vision_test/conveyor_vision_test/topview_color_detector.py`
- Modify/Test: `workspaces/지웅/ros2_ws/src/conveyor_vision_test/test/test_topview_color_detector.py`

**Implementation sketch:**
```python
class AsyncConveyorModbusWriter:
    def __init__(self, host, port, device_id, timeout, zero_based_addresses=True, dry_run=False):
        self.latest_state = None
        self.thread = None
        self.loop = None
        self.stop_event = threading.Event()

    def start(self):
        # daemon thread에서 asyncio loop 시작
        ...

    def submit_state(self, state):
        # callback에서는 latest_state만 교체하고 return
        # queue maxsize=1 또는 latest-wins lock 사용
        ...

    async def _run(self):
        # AsyncModbusTcpClient 연결/재연결
        # latest_state가 바뀌었을 때만 write 수행
        ...

    async def _write_state(self, client, state):
        # PC는 40021/40022/40025/40026/40027 중심으로 쓴다.
        # 40023/40024는 Pi ownership이므로 덮어쓰지 않는다.
        ...
```

**Important design choices:**
- `queue maxsize=1` 또는 `latest_state` 방식으로 오래된 frame 결과는 버린다.
- 같은 state 반복 write는 생략한다.
- 연결 실패 시 image callback을 막지 않고 async worker에서 재시도한다.
- `modbus_dry_run:=true`는 계속 유지해 hardware 없이 로그 검증 가능하게 한다.
- 초기 상태 write는 `stop + speed`까지만 하거나, Pi status/error register는 쓰지 않는다.

**Verification:**
```bash
/usr/bin/python3 -m pytest workspaces/지웅/ros2_ws/src/conveyor_vision_test/test -q
cd workspaces/지웅/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select conveyor_vision_test
colcon test --packages-select conveyor_vision_test
```

---

### Task 4: Raspberry Pi controller 디렉터리 생성

**Objective:** ROS 패키지와 분리된 Pi 전용 Modbus client + GPIO motor controller 코드를 만든다.

**Files:**
- Create: `workspaces/지웅/conveyor/pi_controller/README.md`
- Create: `workspaces/지웅/conveyor/pi_controller/requirements.txt`
- Create: `workspaces/지웅/conveyor/pi_controller/register_map.py`
- Create: `workspaces/지웅/conveyor/pi_controller/conveyor_motor.py`
- Create: `workspaces/지웅/conveyor/pi_controller/conveyor_modbus_client_controller.py`
- Create: `workspaces/지웅/conveyor/pi_controller/tests/test_register_map.py`

**register_map.py constants:**
```python
HOLDING_REGISTER_BASE = 40001
CONVEYOR_COMMAND = 40021
CONVEYOR_SPEED_CMD = 40022
CONVEYOR_STATUS = 40023
CONVEYOR_ERROR_CODE = 40024
CUBE_DETECTED = 40025
CUBE_COLOR = 40026
LAST_VISION_EVENT = 40027

COMMAND_STOP = 0
COMMAND_RUN_CLOCKWISE = 1
COMMAND_RUN_COUNTER_CLOCKWISE = 2
COMMAND_RESET = 3
COMMAND_EMERGENCY_STOP = 4

def protocol_address(register: int) -> int:
    return register - HOLDING_REGISTER_BASE
```

**Verification:**
```bash
python3 -m pytest workspaces/지웅/conveyor/pi_controller/tests -q
```

---

### Task 5: Pi Modbus async client controller 작성

**Objective:** Raspberry Pi가 `pymodbus==3.13.1`의 `AsyncModbusTcpClient`로 외부 server `192.168.110.109:50200`에 접속해 holding register `20~29`를 읽고/쓴다.

**Files:**
- Modify: `workspaces/지웅/conveyor/pi_controller/conveyor_modbus_client_controller.py`

**Client behavior:**
```python
from pymodbus.client import AsyncModbusTcpClient

client = AsyncModbusTcpClient("192.168.110.109", port=50200, timeout=1.0)
await client.connect()
rr = await client.read_holding_registers(20, count=10, device_id=1)
await client.write_registers(22, [status, error_code], device_id=1)  # 40023/40024
```

**Plan notes:**
- Pi는 server를 열지 않고, 외부 Modbus server에 붙는 client다.
- 40021/40022를 20~50ms 또는 50~100ms 주기로 polling한다.
- command/speed가 바뀐 경우에만 motor method를 호출한다.
- Pi는 실제 모터 상태를 기준으로 40023/40024를 write한다.
- 연결 실패 시 모터를 안전 정지하고 reconnect backoff를 둔다.

**Verification:**
```bash
ssh ssafy@192.168.110.139
cd /home/ssafy/SmartFarmProject/workspaces/지웅/conveyor/pi_controller
python3 conveyor_modbus_client_controller.py   --server-host 192.168.110.109   --server-port 50200   --dry-run-motor
```

다른 터미널 또는 PC에서 command register를 write해 Pi dry-run 로그가 바뀌는지 확인한다.

---

### Task 6: Pi motor controller를 Modbus client polling loop와 분리

**Objective:** Modbus polling/write loop가 모터 step pulse 때문에 막히지 않게 한다.

**Files:**
- Modify: `workspaces/지웅/conveyor/pi_controller/conveyor_motor.py`
- Modify: `workspaces/지웅/conveyor/pi_controller/conveyor_modbus_client_controller.py`

**Reference GPIO mapping from `ref/conveyor/conveyor_test.py`:**
```python
DIR_PIN = 17
STEP_PIN = 27
ENABLE_PIN = 22
BUTTON1_PIN = 23
BUTTON2_PIN = 24
```

**Design:**
- `ConveyorMotor`는 `start(direction, speed_cmd)`, `stop()`, `emergency_stop()`, `close()` 메서드를 가진다.
- 실제 step pulse는 dedicated thread에서 처리한다.
- Modbus polling loop는 20~50ms마다 40021/40022를 읽고, command 변경 시에만 motor method를 호출한다.
- `--dry-run-motor` 옵션에서는 GPIO import 없이 로그만 출력한다.
- Pi가 실제 수행한 상태를 40023/40024에 쓴다.

**Command mapping:**
```text
0 stop                  -> motor.stop(), status=idle
1 run_clockwise         -> DIR=0, ENABLE=0, step loop start, status=running
2 run_counter_clockwise -> DIR=1, ENABLE=0, step loop start, status=running
3 reset                 -> motor.stop(), error=0, status=idle
4 emergency_stop        -> motor.emergency_stop(), ENABLE=1, status=emergency_stopped
```

**Verification ladder:**
1. PC에서 `--dry-run-motor`로 command 변경 로그 확인.
2. Pi에서 GPIO 없이 `--dry-run-motor` 실행 후 Modbus client read/write 확인.
3. Pi에서 GPIO 실제 연결 후 `stop`, `run_clockwise`, `run_counter_clockwise`, `emergency_stop` 순서로 짧게 테스트.
4. 긴급정지 후 ENABLE이 비활성 상태인지 확인.

---

### Task 7: PC 수동 command tool을 async client로 전환

**Objective:** `conveyor_modbus_command`도 3.13.1 async client 기준으로 맞춘다.

**Files:**
- Modify: `workspaces/지웅/ros2_ws/src/conveyor_vision_test/conveyor_vision_test/conveyor_modbus_command.py`

**Behavior:**
- CLI는 그대로 유지한다.
- 내부 구현은 `asyncio.run(...)` + `AsyncModbusTcpClient`로 바꾼다.
- command tool은 40021/40022만 쓴다.

**Verification:**
```bash
ros2 run conveyor_vision_test conveyor_modbus_command emergency_stop --dry-run
ros2 run conveyor_vision_test conveyor_modbus_command run_clockwise --speed 100 --host 192.168.110.109 --port 50200
```

---

### Task 8: 통합 smoke test 작성

**Objective:** 실제 하드웨어 전, 외부 Modbus server 또는 localhost mock server에 대해 PC client와 Pi client controller의 register write/read 흐름을 검증한다.

**Files:**
- Create: `workspaces/지웅/conveyor/pi_controller/tests/test_async_client_controller_smoke.py` 또는 script `smoke_async_modbus_clients.py`

**Test cases:**
1. 외부 server `192.168.110.109:50200` 또는 localhost mock server에서 40021~40030 read 가능.
2. PC client가 40021=1, 40022=100, 40025=1, 40026=1, 40027=1 write.
3. Pi motor dry-run loop가 command 변경을 감지해 `run_clockwise` 상태가 된다.
4. PC client가 40021=0 write.
5. Pi status가 idle로 돌아간다.
6. `emergency_stop` command가 status `4`로 반영된다.

---

### Task 9: ROS detector 통합 검증

**Objective:** D435i/OpenCV loop와 async Modbus writer가 함께 돌아도 frame callback이 막히지 않는지 확인한다.

**Commands:**
```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select conveyor_vision_test
source install/setup.bash

ros2 run conveyor_vision_test topview_color_detector --ros-args   -p show_windows:=false   -p modbus_enabled:=true   -p modbus_dry_run:=true   -p conveyor_speed_cmd:=100
```

Pi client controller 연결 후:
```bash
ros2 run conveyor_vision_test topview_color_detector --ros-args   -p modbus_enabled:=true   -p modbus_host:=192.168.110.109   -p modbus_port:=50200   -p conveyor_run_command:=run_clockwise   -p conveyor_speed_cmd:=100
```

**Acceptance criteria:**
- image callback 처리 로그/화면이 Modbus write 지연에 의해 멈추지 않는다.
- 같은 state 반복 write는 줄어든다.
- Pi status register를 PC가 덮어쓰지 않는다.
- emergency_stop command가 즉시 반영된다.

---

## 3. 실행 순서 요약

1. 문서/requirements를 `pymodbus==3.13.1`로 갱신한다.
2. PC 쪽 기존 동기 Modbus wrapper를 async writer 구조로 교체한다.
3. Raspberry Pi 전용 `pi_controller` 디렉터리를 만들고 register map을 공유한다.
4. 외부 Modbus server `192.168.110.109:50200` 연결을 확인한다.
5. Pi에서 async Modbus client controller를 `--dry-run-motor`로 먼저 실행한다.
6. Pi motor controller를 dry-run → 실제 GPIO 순서로 붙인다.
7. localhost/mock smoke → external server read/write smoke → ROS detector dry-run → ROS detector + Pi client controller → 실제 컨베이어 순서로 검증한다.

## 4. 남은 확인 질문

1. Modbus server `192.168.110.109:50200`이 기존대로 유지되는지 최종 확인 필요.
2. Raspberry Pi 5 접속 대상은 `ssafy@192.168.110.139`로 기록하되, 비밀번호는 문서에 저장하지 않는다.
3. `speed_cmd=100`을 step delay로 어떻게 환산할지 결정 필요. MVP에서는 `100=현재 ref 코드의 0.0001s step delay`로 두고, 나중에 속도 테이블로 바꾸는 것을 권장.
4. 수동 버튼 `BUTTON1_PIN=23`, `BUTTON2_PIN=24`를 계속 살릴지, Modbus 제어만 사용할지 확인 필요.
5. Dashboard/서버가 register write까지 할지, 아니면 read-only 상태 확인만 할지 확인 필요. 버벅임과 race condition을 줄이려면 MVP에서는 PC vision/safety command만 write하고 dashboard는 read-only가 좋다.

## 5. Raspberry Pi client controller 상세 구현 계획

라즈베리파이에 올릴 실제 Modbus client + GPIO controller 구현 계획은 별도 문서에 둔다.

- Repo docs: `docs/Conveyor_Pi_Modbus_Client_Controller_구현_계획.md`
- Obsidian: `[[Conveyor Pi Modbus Client Controller 구현 계획]]`

주요 반영 사항:
- `BUTTON1_PIN=23`: 긴급정지
- `BUTTON2_PIN=24`: 재시작
- 속도/가감속은 `ref/conveyor/conv_profile_지웅.py`의 `TargetSpeed=0.0001`, `InitialSpeed=0.0005`, `RATIO=0.0000005`를 기준으로 한다.

# Conveyor Pi Modbus Client Controller Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Raspberry Pi 5(`ssafy@192.168.110.139`)에 올릴 `pymodbus==3.13.1` 기반 비동기 Modbus client + GPIO 컨베이어 제어 프로그램을 만든다. 이 프로그램은 외부 Modbus server `192.168.110.109:50200`의 register를 읽어 컨베이어를 구동하고, 긴급정지/재시작 버튼 입력과 실제 모터 상태를 Modbus register에 반영한다.

**Architecture:** Raspberry Pi는 Modbus server가 아니라 **Modbus client**다. Pi controller는 `AsyncModbusTcpClient`로 `40021~40030` register block을 polling/write하고, 모터 step pulse는 별도 thread에서 `gpiod`로 `DIR/STEP/ENABLE`을 제어한다. 버튼 polling은 제어 루프와 분리하되, 버튼 이벤트 발생 시 모터를 즉시 정지/재시작하고 status/error register를 갱신한다.

**Tech Stack:** Raspberry Pi 5 Raspbian, Python 3, `pymodbus==3.13.1`, `asyncio`, `gpiod`, GPIO `DIR=17`, `STEP=27`, `ENABLE=22`, buttons `23/24`, Modbus TCP server `192.168.110.109:50200`, holding registers `40021~40030` / pymodbus protocol addresses `20~29`.

---

## 0. 확정 입력과 참고 코드

### 확정 입력

- Modbus server: `192.168.110.109:50200`
- Raspberry Pi SSH target: `ssafy@192.168.110.139`
- 비밀번호는 문서/코드에 저장하지 않는다.
- Raspberry Pi는 Modbus **client**다.
- Pi client는 Modbus client + GPIO 제어를 한 프로그램 안에 포함한다.
- 기존 버튼 2개는 다음 용도로 재정의한다.
  - `BUTTON1_PIN=23`: 긴급정지
  - `BUTTON2_PIN=24`: 재시작
- 속도/가감속은 `ref/conveyor/conv_profile_지웅.py`의 모션 프로파일을 참고한다.

### 참고한 모션 프로파일

`/home/ssafy/work/SmartFarmProject/workspaces/지웅/conveyor/ref/conveyor/conv_profile_지웅.py`

핵심 상수:

```python
DIR_PIN = 17
STEP_PIN = 27
ENABLE_PIN = 22
btn1 = 23
btn2 = 24

TargetSpeed = 0.0001
InitialSpeed = 0.0005
RATIO = 0.0000005
```

해석:
- `InitialSpeed=0.0005`: 출발/정지 근처의 느린 step delay
- `TargetSpeed=0.0001`: 정상 운전 목표 step delay
- `RATIO=0.0000005`: step loop마다 delay를 줄이거나 늘리는 가감속 변화량
- GPIO enable은 기존 코드 기준 `enable_line.set_value(0)`이 활성, `1`이 비활성
- 기존 코드의 방향은 CW에서 `dir_line.set_value(0)`, CCW에서 `dir_line.set_value(1)`로 사용한다.

---

## 1. 최종 제어 구조

```text
PC / ROS2 / D435i
  └─ Async Modbus client
      ├─ 40021 conveyor_command write
      ├─ 40022 conveyor_speed_cmd write
      ├─ 40025 cube_detected write
      ├─ 40026 cube_color write
      └─ 40027 last_vision_event write

External Modbus TCP server
  └─ 192.168.110.109:50200
      └─ holding registers 40021~40030

Raspberry Pi 5 / Raspbian
  └─ conveyor_modbus_client_controller.py
      ├─ AsyncModbusTcpClient polling
      │   ├─ read 40021 conveyor_command
      │   └─ read 40022 conveyor_speed_cmd
      ├─ GPIO motor controller
      │   ├─ DIR 17
      │   ├─ STEP 27
      │   └─ ENABLE 22
      ├─ button polling
      │   ├─ BUTTON1 23: emergency_stop
      │   └─ BUTTON2 24: restart/reset emergency latch
      └─ Modbus status write
          ├─ 40023 conveyor_status
          └─ 40024 conveyor_error_code
```

---

## 2. Register map / ownership

| Register | Address | Name | Pi 동작 |
|---:|---:|---|---|
| 40021 | 20 | `conveyor_command` | Pi가 읽음. `0 stop`, `1 cw`, `2 ccw`, `3 reset`, `4 emergency_stop` |
| 40022 | 21 | `conveyor_speed_cmd` | Pi가 읽음. 목표 속도 scale 또는 profile preset |
| 40023 | 22 | `conveyor_status` | Pi가 씀. 실제 모터 상태 |
| 40024 | 23 | `conveyor_error_code` | Pi가 씀. GPIO/Modbus/button/error 상태 |
| 40025 | 24 | `cube_detected` | PC vision이 씀. Pi는 필요 시 read-only 참고 |
| 40026 | 25 | `cube_color` | PC vision이 씀 |
| 40027 | 26 | `last_vision_event` | PC vision이 씀 |
| 40028 | 27 | `reserved_conveyor_1` | 추후 heartbeat 후보 |
| 40029 | 28 | `reserved_conveyor_2` | 추후 Pi local emergency latch 후보 |
| 40030 | 29 | `reserved_conveyor_3` | 추후 확장 |

### status enum

```python
STATUS_IDLE = 0
STATUS_RUNNING = 1
STATUS_DELIVERED = 2
STATUS_ERROR = 3
STATUS_EMERGENCY_STOPPED = 4
```

### error enum 초안

```python
ERROR_NONE = 0
ERROR_MODBUS_CONNECT_FAILED = 1
ERROR_MODBUS_READ_FAILED = 2
ERROR_MODBUS_WRITE_FAILED = 3
ERROR_GPIO_INIT_FAILED = 4
ERROR_INVALID_COMMAND = 5
ERROR_LOCAL_EMERGENCY_STOP = 6
```

---

## 3. 버튼 정책 초안

### BUTTON1 / GPIO 23: 긴급정지

누르는 즉시:
1. 모터 step thread 정지
2. `ENABLE=1`로 모터 disable
3. local emergency latch 활성화
4. Modbus write:
   - `40023 conveyor_status = 4 emergency_stopped`
   - `40024 conveyor_error_code = 6 local_emergency_stop`
5. emergency latch가 켜져 있는 동안 PC가 `run_clockwise`를 써도 Pi는 모터를 돌리지 않음

### BUTTON2 / GPIO 24: 재시작

누르는 즉시:
1. local emergency latch 해제
2. Modbus write:
   - `40024 error_code = 0 none`
   - `40023 status = 0 idle`
3. 이후 server의 `40021`이 다시 `1 cw` 또는 `2 ccw`로 바뀌면 정상 구동

> 기본 안전 정책: 재시작 버튼을 누른 순간 바로 모터를 재가동하지 않고, emergency latch만 해제한다. 실제 재가동은 Modbus command가 다시 run으로 들어왔을 때 수행한다. 이게 가장 안전하다.

---

## 4. 속도/모션 프로파일 정책

`conv_profile_지웅.py`의 가감속 프로파일을 보존하되, 코드 구조는 함수/클래스로 분리한다.

### 기본 profile

```python
INITIAL_STEP_DELAY_SEC = 0.0005
TARGET_STEP_DELAY_SEC = 0.0001
RAMP_DELTA_SEC = 0.0000005
```

### speed_cmd 해석 초안

MVP에서는 `40022 conveyor_speed_cmd`를 다음처럼 해석한다.

```text
0       -> 기본 목표 속도 사용, TARGET_STEP_DELAY_SEC=0.0001
1~100   -> percent scale. 100은 ref의 TargetSpeed 0.0001, 낮을수록 더 느리게
>100    -> 100으로 clamp
```

권장 함수:

```python
def speed_cmd_to_target_delay(speed_cmd: int) -> float:
    speed = max(1, min(int(speed_cmd or 100), 100))
    # speed=100 -> 0.0001
    # speed=1   -> 0.0005에 가까운 매우 느린 속도
    return INITIAL_STEP_DELAY_SEC - (INITIAL_STEP_DELAY_SEC - TARGET_STEP_DELAY_SEC) * (speed / 100.0)
```

> 이 매핑은 안전한 초안이다. 실제 컨베이어 속도가 너무 빠르거나 느리면 speed table로 바꾸는 게 좋다.

---

## 5. 파일 구조 계획

```text
workspaces/지웅/conveyor/pi_controller/
  README.md
  requirements.txt
  register_map.py
  motion_profile.py
  conveyor_motor.py
  conveyor_modbus_client_controller.py
  run_pi_controller.sh
  tests/
    test_register_map.py
    test_motion_profile.py
    test_controller_logic.py
```

---

## 6. 단계별 구현 계획

### Task 1: register_map.py 작성

**Objective:** Modbus register, command/status/error enum, address conversion을 한 곳에 모은다.

**Files:**
- Create: `workspaces/지웅/conveyor/pi_controller/register_map.py`
- Test: `workspaces/지웅/conveyor/pi_controller/tests/test_register_map.py`

**Implementation details:**
- `protocol_address(40021) == 20`
- `protocol_address(40030) == 29`
- command/status/error enum 상수 정의

**Verification:**
```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/conveyor/pi_controller
python3 -m pytest tests/test_register_map.py -q
```
Expected: pass

---

### Task 2: motion_profile.py 작성

**Objective:** `conv_profile_지웅.py`의 가감속 상수를 안전한 함수로 분리한다.

**Files:**
- Create: `workspaces/지웅/conveyor/pi_controller/motion_profile.py`
- Test: `workspaces/지웅/conveyor/pi_controller/tests/test_motion_profile.py`

**Implementation details:**
- `INITIAL_STEP_DELAY_SEC = 0.0005`
- `TARGET_STEP_DELAY_SEC = 0.0001`
- `RAMP_DELTA_SEC = 0.0000005`
- `speed_cmd_to_target_delay(speed_cmd)` 구현
- `next_accel_delay(current_delay, target_delay)` 구현
- `next_decel_delay(current_delay, initial_delay)` 구현

**Verification:**
- speed 100은 `0.0001`에 가까움
- speed 1은 `0.0005`에 가까움
- acceleration은 delay를 줄임
- deceleration은 delay를 늘림

---

### Task 3: conveyor_motor.py 작성

**Objective:** GPIO 제어와 step pulse thread를 Modbus 로직과 분리한다.

**Files:**
- Create: `workspaces/지웅/conveyor/pi_controller/conveyor_motor.py`
- Test: `workspaces/지웅/conveyor/pi_controller/tests/test_controller_logic.py`

**Implementation details:**
- `ConveyorMotor(dry_run=False, gpio_chip='gpiochip0')`
- methods:
  - `start_clockwise(speed_cmd)`
  - `start_counter_clockwise(speed_cmd)`
  - `stop()`
  - `emergency_stop()`
  - `restart_latch()` 또는 latch는 controller가 관리
  - `close()`
- 실제 GPIO import는 `dry_run=False`일 때만 수행
- `dry_run=True`에서는 GPIO 없이 로그와 내부 상태만 변경
- step thread는 lock/event로 종료 가능해야 함
- CW: `DIR=0`, CCW: `DIR=1`
- run: `ENABLE=0`, stop/emergency: `ENABLE=1`

**Verification:**
- dry-run에서 GPIO 없이 import/실행 가능
- start/stop/emergency 상태 전이 테스트
- thread가 중복 생성되지 않는지 테스트

---

### Task 4: button policy 구현

**Objective:** BUTTON1 긴급정지, BUTTON2 재시작 정책을 controller 상태 머신에 반영한다.

**Files:**
- Modify: `workspaces/지웅/conveyor/pi_controller/conveyor_motor.py`
- Modify: `workspaces/지웅/conveyor/pi_controller/conveyor_modbus_client_controller.py`
- Test: `workspaces/지웅/conveyor/pi_controller/tests/test_controller_logic.py`

**Implementation details:**
- button input은 active-low로 본다. `0 == pressed`, `1 == released`
- debounce 기본값: `0.05s`
- BUTTON1 pressed:
  - motor emergency_stop
  - local emergency latch set
  - status/error write 예약
- BUTTON2 pressed:
  - local emergency latch clear
  - motor는 idle 유지
  - status/error reset write 예약
- 재시작 버튼은 모터를 바로 run하지 않는다.

**Verification:**
- emergency latch 상태에서는 run command가 들어와도 motor start 안 됨
- restart 후 run command가 다시 들어오면 motor start 가능

---

### Task 5: async Modbus client controller 작성

**Objective:** Pi가 외부 Modbus server를 polling하고 status/error를 write한다.

**Files:**
- Create: `workspaces/지웅/conveyor/pi_controller/conveyor_modbus_client_controller.py`

**Implementation details:**
- CLI args:
  - `--server-host 192.168.110.109`
  - `--server-port 50200`
  - `--device-id 1`
  - `--poll-interval-sec 0.05`
  - `--dry-run-motor`
  - `--dry-run-modbus` for local logic smoke
  - `--gpio-chip gpiochip0`
- main loop:
  1. connect with `AsyncModbusTcpClient`
  2. read holding registers address `20`, count `10`
  3. parse command/speed
  4. apply local emergency latch policy
  5. call motor method only when command/speed changes
  6. write 40023/40024 on status/error changes
  7. reconnect with backoff on failure

**pymodbus 3.13.1 call shape:**

```python
client = AsyncModbusTcpClient(host, port=port, timeout=timeout)
await client.connect()
rr = await client.read_holding_registers(20, count=10, device_id=device_id)
await client.write_registers(22, [status, error_code], device_id=device_id)
```

**Verification:**
```bash
python3 conveyor_modbus_client_controller.py   --server-host 192.168.110.109   --server-port 50200   --dry-run-motor
```
Expected:
- server connect 성공 또는 명확한 reconnect 로그
- command register 변경 시 dry-run motor action 로그
- status/error write 로그

---

### Task 6: run script / README 작성

**Objective:** Pi에서 바로 실행 가능한 명령을 문서화한다.

**Files:**
- Create: `workspaces/지웅/conveyor/pi_controller/run_pi_controller.sh`
- Create/Modify: `workspaces/지웅/conveyor/pi_controller/README.md`

**run_pi_controller.sh:**
```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 conveyor_modbus_client_controller.py   --server-host 192.168.110.109   --server-port 50200   --device-id 1
```

**README must include:**
- Pi install commands
- `pymodbus==3.13.1` install
- `gpiod` 설치/확인
- dry-run motor 실행
- 실제 GPIO 실행
- 버튼 동작 설명
- emergency_stop 안전 주의

---

### Task 7: PC에서 Pi 배포/검증 절차

**Objective:** 코드를 Pi로 옮기고 dry-run부터 확인한다.

**Commands:**
```bash
rsync -av /home/ssafy/work/SmartFarmProject/workspaces/지웅/conveyor/pi_controller/   ssafy@192.168.110.139:/home/ssafy/SmartFarmProject/workspaces/지웅/conveyor/pi_controller/

ssh ssafy@192.168.110.139
cd /home/ssafy/SmartFarmProject/workspaces/지웅/conveyor/pi_controller
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python conveyor_modbus_client_controller.py --dry-run-motor
```

> 비밀번호는 명령/문서에 넣지 않는다. SSH 프롬프트에서 직접 입력한다.

---

### Task 8: 단계별 실기기 검증

**Objective:** 실제 컨베이어를 안전하게 검증한다.

**Verification ladder:**
1. PC local unit tests 통과
2. Pi에서 `--dry-run-motor`로 Modbus server 연결 확인
3. PC에서 manual command로 `40021=1`, `40022=100` write
4. Pi dry-run 로그에서 `start_clockwise` 확인
5. PC에서 `stop` write 후 Pi dry-run 로그에서 stop 확인
6. Pi 실제 GPIO 연결 후 motor 무부하 상태에서 `stop` 확인
7. 짧게 `run_clockwise` 확인
8. BUTTON1 긴급정지 확인: 즉시 motor disable + status/error write
9. BUTTON2 재시작 확인: latch 해제 + idle/error none write, 바로 재구동하지 않음
10. ROS detector와 함께 연결해 큐브 감지 시 run, 10프레임 미검출 시 stop 확인

---

## 7. 모호한 부분 / 확인 질문

아래는 구현 전 확인하면 더 정확해진다. 일단 계획은 안전한 기본값으로 잡았다.

1. 버튼 매핑은 `GPIO23=긴급정지`, `GPIO24=재시작`으로 진행해도 되는가?
2. 재시작 버튼은 지금 계획처럼 **emergency latch만 해제하고 바로 모터를 돌리지 않는 방식**이 맞는가?
3. `speed_cmd=100`을 `TargetSpeed=0.0001`로 보는 percent mapping으로 진행해도 되는가?
4. 긴급정지 버튼이 눌렸을 때 Pi는 `40021` command register를 바꾸지 않고 `40023/40024`만 갱신하는 것으로 확정했다.
5. button debounce는 기본 `50ms`로 충분한가?

---

## 8. 2026-06-24 구현/배포 결과

구현 완료 파일:

```text
workspaces/지웅/conveyor/pi_controller/register_map.py
workspaces/지웅/conveyor/pi_controller/motion_profile.py
workspaces/지웅/conveyor/pi_controller/conveyor_motor.py
workspaces/지웅/conveyor/pi_controller/conveyor_modbus_client_controller.py
workspaces/지웅/conveyor/pi_controller/run_pi_controller.sh
workspaces/지웅/conveyor/pi_controller/README.md
workspaces/지웅/conveyor/pi_controller/tests/
```

로컬 검증:
- `python3 -m py_compile register_map.py motion_profile.py conveyor_motor.py conveyor_modbus_client_controller.py` 통과
- `python3 -m pytest tests -q` 결과 `13 passed`
- `./run_pi_controller.sh --dry-run-motor --dry-run-modbus` smoke 실행 성공

Raspberry Pi 배포:
- 배포 위치: `ssafy@192.168.110.139:/home/ssafy/SmartFarmProject/workspaces/지웅/conveyor/pi_controller`
- `.venv` 생성 완료: `python3 -m venv --system-site-packages .venv`
- `pymodbus==3.13.1` 설치 확인
- `gpiod import ok` 확인
- `run_pi_controller.sh` 실행 권한 설정 완료
- Pi local dry-run smoke 실행 성공

현재 blocker:
- Pi에서 Modbus server `192.168.110.109:50200` 접속은 실패했다.
- Pi 기준 `ping 192.168.110.109` 결과 100% packet loss.
- Pi 기준 TCP check 결과 `No route to host`.
- 따라서 실제 external server 연동은 서버 전원/네트워크/라우팅 확인 후 재검증해야 한다.

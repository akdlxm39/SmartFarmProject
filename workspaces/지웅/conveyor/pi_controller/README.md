# Raspberry Pi Conveyor Modbus Client Controller

Raspberry Pi 5에서 실행하는 컨베이어 제어 프로그램입니다.

- Modbus server: `192.168.110.109:50200`
- Raspberry Pi: `ssafy@192.168.110.139`
- Pi 역할: **Modbus client + GPIO motor controller**
- Python Modbus: `pymodbus==3.13.1`

> 비밀번호는 문서/스크립트에 저장하지 않습니다. SSH 프롬프트에서 직접 입력합니다.

## Register ownership

| Register | Address | Name | Owner |
|---:|---:|---|---|
| 40021 | 20 | `conveyor_command` | PC/manual client writes, Pi reads |
| 40022 | 21 | `conveyor_speed_cmd` | PC/manual client writes, Pi reads |
| 40023 | 22 | `conveyor_status` | Pi writes |
| 40024 | 23 | `conveyor_error_code` | Pi writes |
| 40025 | 24 | `cube_detected` | PC vision writes |
| 40026 | 25 | `cube_color` | PC vision writes |
| 40027 | 26 | `last_vision_event` | PC vision writes |
| 40028~40030 | 27~29 | reserved | future |

## Command values

```text
0 stop
1 run_clockwise
2 run_counter_clockwise
3 reset
4 emergency_stop
```

## Status values

```text
0 idle
1 running
2 delivered
3 error
4 emergency_stopped
```

## GPIO pins

Reference: `../ref/conveyor/conv_profile_지웅.py`

```text
DIR=17
STEP=27
ENABLE=22  # 0 active, 1 disabled
BUTTON1=23 # emergency stop
BUTTON2=24 # restart / emergency latch clear
```

## Button policy

### BUTTON1 / GPIO 23: emergency stop

- Immediately disables motor with `ENABLE=1`.
- Sets local emergency latch.
- Writes:
  - `40023 status = 4 emergency_stopped`
  - `40024 error_code = 6 local_emergency_stop`
- Does **not** rewrite `40021 conveyor_command`.
- While latched, run commands are ignored.

### BUTTON2 / GPIO 24: restart

- Clears local emergency latch.
- Writes:
  - `40023 status = 0 idle`
  - `40024 error_code = 0 none`
- Does not start the motor directly. A new Modbus run command is required.

## Install on Raspberry Pi

```bash
cd /home/ssafy/SmartFarmProject/workspaces/지웅/conveyor/pi_controller
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If `gpiod` is missing on Raspbian, install the system package:

```bash
sudo apt update
sudo apt install -y python3-libgpiod gpiod
```

## Dry-run motor test

This connects to the real Modbus server but does not touch GPIO:

```bash
./run_pi_controller.sh --dry-run-motor
```

Local logic test without real Modbus server or GPIO:

```bash
./run_pi_controller.sh --dry-run-motor --dry-run-modbus
```

## Real GPIO run

Only run this when the conveyor area is safe:

```bash
./run_pi_controller.sh
```

## Manual command from PC

Example from the ROS2 package after it is updated to async client:

```bash
ros2 run conveyor_vision_test conveyor_modbus_command run_clockwise --speed 100 --host 192.168.110.109 --port 50200
ros2 run conveyor_vision_test conveyor_modbus_command stop --host 192.168.110.109 --port 50200
ros2 run conveyor_vision_test conveyor_modbus_command emergency_stop --host 192.168.110.109 --port 50200
```

## Local tests

```bash
python3 -m pytest tests -q
python3 -m py_compile register_map.py motion_profile.py conveyor_motor.py conveyor_modbus_client_controller.py
```

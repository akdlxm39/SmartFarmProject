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

`conveyor_motor.py` uses the libgpiod v1 Python API (`gpiod.Chip(...).get_line`, `LINE_REQ_DIR_OUT`). On Raspberry Pi OS/Ubuntu, install the OS GPIO binding first, then create the venv with system packages visible.

```bash
sudo apt update
sudo apt install -y gpiod python3-libgpiod

cd /home/ssafy/SmartFarmProject/workspaces/지웅/conveyor/pi_controller
rm -rf .venv
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python - <<'PY'
import gpiod, pymodbus, sys
print(sys.executable)
print('gpiod:', gpiod.__file__)
print('pymodbus:', pymodbus.__version__)
print('has get_line:', hasattr(gpiod.Chip('gpiochip0'), 'get_line'))
PY
```

Do **not** blindly install the newest PyPI `gpiod` package if the import works from `python3-libgpiod`; newer libgpiod v2-style bindings may not expose the v1 `get_line()` API used by this controller.

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

The startup log should now include the GPIO mapping, for example:

```text
GPIO setup chip=gpiochip0 dir=17 step=27 enable=22 enable_active_low=True
motor step loop started direction=clockwise target_delay=...
```

If the Modbus status becomes `running` but the belt does not move, first test the Pi GPIO layer:

```bash
gpioinfo | grep -E 'GPIO17|GPIO22|GPIO27|conveyor'
./run_pi_controller.sh --gpio-chip gpiochip4   # Raspberry Pi 5 alternate chip test
```

If the reference direct-pulse script also does not move the motor, treat it as a driver power / wiring / enable-polarity / GPIO chip issue rather than a Modbus issue.

## Direct GPIO pulse diagnostic

Use this after stopping all running conveyor controller processes. It bypasses Modbus and drives STEP/DIR/ENABLE directly.

```bash
# 1) Stop old controller processes first, otherwise GPIO lines remain [used].
pkill -f conveyor_modbus_client_controller.py || true
pkill -f gpio_pulse_diagnostic.py || true

# 2) Confirm the lines are free. If they are still [used], another process is holding them.
gpioinfo | grep -E 'GPIO17|GPIO22|GPIO27|conveyor|diag'

# 3) Slow safe pulse test on the default chip.
source .venv/bin/activate
python gpio_pulse_diagnostic.py --gpio-chip gpiochip0 --pulse-delay-sec 0.001 --duration-sec 3

# 4) If the motor does not move, test opposite enable polarity.
python gpio_pulse_diagnostic.py --gpio-chip gpiochip0 --no-enable-active-low --pulse-delay-sec 0.001 --duration-sec 3

# 5) If Pi 5 chip mapping is still suspected, repeat on gpiochip4.
python gpio_pulse_diagnostic.py --gpio-chip gpiochip4 --pulse-delay-sec 0.001 --duration-sec 3
```

Interpretation:
- Diagnostic moves motor: controller/Modbus parameters can be adjusted to match the working chip/polarity/timing.
- Diagnostic does not move motor but GPIO lines are `[used]`: software is toggling GPIO, so inspect driver power, ENA wiring/polarity, STEP/DIR wiring, common ground, and motor driver DIP/current settings.
- `gpioinfo` shows duplicate GPIO17/22/27 entries only because multiple chips expose similarly named lines; use `gpioinfo gpiochip0` and `gpioinfo gpiochip4` separately to distinguish them.

## Manual command from PC

Example from the ROS2 package after it is updated to async client:

```bash
ros2 run realsense conveyor_modbus_command run_clockwise --speed 100 --host 192.168.110.109 --port 50200
ros2 run realsense conveyor_modbus_command stop --host 192.168.110.109 --port 50200
ros2 run realsense conveyor_modbus_command emergency_stop --host 192.168.110.109 --port 50200
```

## Local tests

```bash
python3 -m pytest tests -q
python3 -m py_compile register_map.py motion_profile.py conveyor_motor.py conveyor_modbus_client_controller.py
```

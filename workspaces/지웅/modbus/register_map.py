"""SmartFarmProject shared Modbus register map.

Human-facing holding register numbers use the usual 4xxxx notation. Pymodbus
uses zero-based protocol addresses, so 40021 maps to address 20 when
``zero_based=True``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

HOLDING_REGISTER_BASE = 40001
DEFAULT_SERVER_HOST = "192.168.110.109"
DEFAULT_SERVER_PORT = 50200
DEFAULT_DEVICE_ID = 1

# Conveyor block, already used by PC vision and Raspberry Pi controller.
REGISTER_CONVEYOR_COMMAND = 40021
REGISTER_CONVEYOR_SPEED_CMD = 40022
REGISTER_CONVEYOR_STATUS = 40023
REGISTER_CONVEYOR_ERROR_CODE = 40024
REGISTER_CUBE_DETECTED = 40025
REGISTER_CUBE_COLOR = 40026
REGISTER_LAST_VISION_EVENT = 40027
REGISTER_CONVEYOR_RESERVED_1 = 40028
REGISTER_CONVEYOR_RESERVED_2 = 40029
REGISTER_CONVEYOR_RESERVED_3 = 40030

# Future Dobot block. Values are placeholders until the Dobot client is added.
REGISTER_DOBOT_STATUS = 40031
REGISTER_DOBOT_ERROR_CODE = 40032
REGISTER_DOBOT_CURRENT_STEP = 40033
REGISTER_DOBOT_TARGET_SLOT = 40034
REGISTER_DOBOT_QUALITY_RESULT = 40035
REGISTER_DOBOT_LAST_EVENT = 40036
REGISTER_DOBOT_BUSY = 40037
REGISTER_DOBOT_HEARTBEAT = 40038
REGISTER_DOBOT_RESERVED_START = 40039
REGISTER_DOBOT_RESERVED_END = 40050

# Future TurtleBot block. Values are placeholders until the TurtleBot client is added.
REGISTER_TURTLEBOT_STATUS = 40051
REGISTER_TURTLEBOT_ERROR_CODE = 40052
REGISTER_TURTLEBOT_NAV_STATE = 40053
REGISTER_TURTLEBOT_CURRENT_GOAL = 40054
REGISTER_TURTLEBOT_BATTERY_PERCENT = 40055
REGISTER_TURTLEBOT_LAST_EVENT = 40056
REGISTER_TURTLEBOT_HEARTBEAT = 40057
REGISTER_TURTLEBOT_RESERVED_START = 40058
REGISTER_TURTLEBOT_RESERVED_END = 40070

REGISTER_SYSTEM_HEARTBEAT = 40071
REGISTER_SYSTEM_MODE = 40072
REGISTER_FARM_STATUS = 40073
REGISTER_SYSTEM_RESERVED_START = 40074
REGISTER_SYSTEM_RESERVED_END = 40100

SHARED_REGISTER_START = REGISTER_CONVEYOR_COMMAND
SHARED_REGISTER_END = REGISTER_SYSTEM_RESERVED_END
SHARED_BLOCK_COUNT = SHARED_REGISTER_END - SHARED_REGISTER_START + 1
SHARED_BLOCK_START_ADDRESS = SHARED_REGISTER_START - HOLDING_REGISTER_BASE
SERVER_HR_COUNT = SHARED_REGISTER_END - HOLDING_REGISTER_BASE + 1

# Conveyor command enum, preserved from existing conveyor clients.
COMMAND_STOP = 0
COMMAND_RUN_CLOCKWISE = 1
COMMAND_RUN_COUNTER_CLOCKWISE = 2
COMMAND_RESET = 3
COMMAND_EMERGENCY_STOP = 4

STATUS_IDLE = 0
STATUS_RUNNING = 1
STATUS_DELIVERED = 2
STATUS_ERROR = 3
STATUS_EMERGENCY_STOPPED = 4

ERROR_NONE = 0
ERROR_MODBUS_CONNECT_FAILED = 1
ERROR_MODBUS_READ_FAILED = 2
ERROR_MODBUS_WRITE_FAILED = 3
ERROR_GPIO_INIT_FAILED = 4
ERROR_INVALID_COMMAND = 5
ERROR_LOCAL_EMERGENCY_STOP = 6

COLOR_NONE = 0
COLOR_RED = 1
COLOR_GREEN = 2
COLOR_UNKNOWN = 3

EVENT_NONE = 0
EVENT_CUBE_DETECTED = 1
EVENT_CUBE_LOST = 2
EVENT_DELIVERED = 3
EVENT_ERROR = 4
EVENT_EMERGENCY_STOP = 5

@dataclass(frozen=True)
class RegisterSpec:
    register: int
    name: str
    owner: str
    description: str = ""

REGISTER_SPECS: List[RegisterSpec] = [
    RegisterSpec(40021, "conveyor_command", "PC vision/manual client", "0 stop, 1 cw, 2 ccw, 3 reset, 4 emergency_stop"),
    RegisterSpec(40022, "conveyor_speed_cmd", "PC vision/manual client", "0 default, 1~100 speed scale"),
    RegisterSpec(40023, "conveyor_status", "Raspberry Pi conveyor client", "actual motor status"),
    RegisterSpec(40024, "conveyor_error_code", "Raspberry Pi conveyor client", "actual controller error"),
    RegisterSpec(40025, "cube_detected", "PC vision client", "0/1"),
    RegisterSpec(40026, "cube_color", "PC vision client", "0 none, 1 red, 2 green, 3 unknown"),
    RegisterSpec(40027, "last_vision_event", "PC vision client", "0 none, 1 detected, 2 lost, 3 delivered, 4 error, 5 estop"),
    RegisterSpec(40028, "reserved_conveyor_1", "reserved", "future conveyor heartbeat/sequence"),
    RegisterSpec(40029, "reserved_conveyor_2", "reserved", "future conveyor extension"),
    RegisterSpec(40030, "reserved_conveyor_3", "reserved", "future conveyor extension"),
    RegisterSpec(40031, "dobot_status", "future Dobot client", "0 idle, 1 moving, 2 gripping, 3 placing, 4 error candidate"),
    RegisterSpec(40032, "dobot_error_code", "future Dobot client", "Dobot/ROS error code"),
    RegisterSpec(40033, "dobot_current_step", "future Dobot client", "harvest/capture/place sequence step"),
    RegisterSpec(40034, "dobot_target_slot", "future Dobot/manual client", "harvest slot or target index"),
    RegisterSpec(40035, "dobot_quality_result", "future vision/Dobot client", "0 unknown, 1 normal, 2 defect candidate"),
    RegisterSpec(40036, "dobot_last_event", "future Dobot client", "last Dobot event enum"),
    RegisterSpec(40037, "dobot_busy", "future Dobot client", "0/1"),
    RegisterSpec(40038, "dobot_heartbeat", "future Dobot client", "incrementing heartbeat"),
    RegisterSpec(40051, "turtlebot_status", "future TurtleBot client", "0 idle, 1 navigating, 2 arrived, 3 error candidate"),
    RegisterSpec(40052, "turtlebot_error_code", "future TurtleBot client", "navigation/ROS error code"),
    RegisterSpec(40053, "turtlebot_nav_state", "future TurtleBot client", "navigation state enum"),
    RegisterSpec(40054, "turtlebot_current_goal", "future backend/TurtleBot client", "goal index"),
    RegisterSpec(40055, "turtlebot_battery_percent", "future TurtleBot client", "0~100"),
    RegisterSpec(40056, "turtlebot_last_event", "future TurtleBot client", "last TurtleBot event enum"),
    RegisterSpec(40057, "turtlebot_heartbeat", "future TurtleBot client", "incrementing heartbeat"),
    RegisterSpec(40071, "system_heartbeat", "server/system", "server-level heartbeat candidate"),
    RegisterSpec(40072, "system_mode", "backend/manual client", "0 manual, 1 auto candidate"),
    RegisterSpec(40073, "farm_status", "backend/system", "overall farm status candidate"),
]

REGISTER_BY_NAME: Dict[str, int] = {spec.name: spec.register for spec in REGISTER_SPECS}


def protocol_address(register_number: int, zero_based: bool = True) -> int:
    """Convert a 4xxxx register number to a pymodbus protocol address."""
    register_number = int(register_number)
    if zero_based:
        if register_number < HOLDING_REGISTER_BASE:
            raise ValueError(f"Register {register_number} is below holding-register base {HOLDING_REGISTER_BASE}")
        return register_number - HOLDING_REGISTER_BASE
    return register_number


def register_number(protocol_addr: int) -> int:
    """Convert a zero-based pymodbus protocol address to 4xxxx notation."""
    return int(protocol_addr) + HOLDING_REGISTER_BASE


def validate_registers(registers: Iterable[int]) -> None:
    for register in registers:
        protocol_address(register)


def initial_holding_registers(count: int = SERVER_HR_COUNT) -> List[int]:
    """Return initial holding-register values sized for 40001..40100."""
    values = [0] * int(count)
    # Safe conveyor defaults.
    values[protocol_address(REGISTER_CONVEYOR_COMMAND)] = COMMAND_STOP
    values[protocol_address(REGISTER_CONVEYOR_SPEED_CMD)] = 0
    values[protocol_address(REGISTER_CONVEYOR_STATUS)] = STATUS_IDLE
    values[protocol_address(REGISTER_CONVEYOR_ERROR_CODE)] = ERROR_NONE
    return values


def markdown_register_table() -> str:
    lines = ["| Register | Address | Name | Owner | Notes |", "|---:|---:|---|---|---|"]
    for spec in REGISTER_SPECS:
        lines.append(
            f"| {spec.register} | {protocol_address(spec.register)} | `{spec.name}` | {spec.owner} | {spec.description} |"
        )
    return "\n".join(lines)

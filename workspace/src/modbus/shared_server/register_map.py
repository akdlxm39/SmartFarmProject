"""SmartFarmProject shared Modbus register map.

Human-facing holding register numbers use the usual 4xxxx notation. Pymodbus
uses zero-based protocol addresses, so 40021 maps to address 20 when
``zero_based=True``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

HOLDING_REGISTER_BASE = 40001
DEFAULT_SERVER_HOST = "192.168.110.109"
DEFAULT_SERVER_PORT = 50200
DEFAULT_DEVICE_ID = 1
U16_MAX = 0xFFFF
U32_MAX = 0xFFFFFFFF

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

# Dobot block. Web should normally use system_command; backend/orchestrator
# translates it into device-level Dobot commands when needed.
REGISTER_DOBOT_COMMAND = 40031
REGISTER_DOBOT_TARGET_SLOT = 40032
REGISTER_DOBOT_COMMAND_SEQ = 40033
REGISTER_DOBOT_COMMAND_ACK_SEQ = 40034
REGISTER_DOBOT_STATUS = 40035
REGISTER_DOBOT_ERROR_CODE = 40036
REGISTER_DOBOT_CURRENT_STEP = 40037
REGISTER_DOBOT_QUALITY_RESULT = 40038
REGISTER_DOBOT_BUSY = 40039
REGISTER_DOBOT_HEARTBEAT = 40040
REGISTER_DOBOT_LAST_EVENT = 40041
REGISTER_DOBOT_RESERVED_START = 40042
REGISTER_DOBOT_RESERVED_END = 40050

# TurtleBot block. Web should normally use system_command; backend/orchestrator
# translates it into device-level TurtleBot commands when needed.
REGISTER_TURTLEBOT_COMMAND = 40051
REGISTER_TURTLEBOT_TARGET_GOAL = 40052
REGISTER_TURTLEBOT_COMMAND_SEQ = 40053
REGISTER_TURTLEBOT_COMMAND_ACK_SEQ = 40054
REGISTER_TURTLEBOT_STATUS = 40055
REGISTER_TURTLEBOT_ERROR_CODE = 40056
REGISTER_TURTLEBOT_NAV_STATE = 40057
REGISTER_TURTLEBOT_BATTERY_PERCENT = 40058
REGISTER_TURTLEBOT_CURRENT_GOAL = 40059
REGISTER_TURTLEBOT_DELIVERY_COUNT_LO = 40060
REGISTER_TURTLEBOT_DELIVERY_COUNT_HI = 40061
REGISTER_TURTLEBOT_LAST_EVENT = 40062
REGISTER_TURTLEBOT_HEARTBEAT = 40063
REGISTER_TURTLEBOT_RESERVED_START = 40064
REGISTER_TURTLEBOT_RESERVED_END = 40070

# Farm/System block. This is the Web/backend-facing shared state surface.
REGISTER_SYSTEM_COMMAND = 40071
REGISTER_SYSTEM_COMMAND_SEQ = 40072
REGISTER_SYSTEM_COMMAND_ACK_SEQ = 40073
REGISTER_SYSTEM_STATE = 40074
REGISTER_SYSTEM_ERROR_CODE = 40075
REGISTER_AI_DEFECT_RATE_BP = 40076
REGISTER_TOTAL_HARVEST_COUNT_LO = 40077
REGISTER_TOTAL_HARVEST_COUNT_HI = 40078
REGISTER_TURTLEBOT_DELIVERY_TOTAL_LO = 40079
REGISTER_TURTLEBOT_DELIVERY_TOTAL_HI = 40080
REGISTER_TOMATO_GOOD_COUNT_LO = 40081
REGISTER_TOMATO_GOOD_COUNT_HI = 40082
REGISTER_TOMATO_BAD_COUNT_LO = 40083
REGISTER_TOMATO_BAD_COUNT_HI = 40084
REGISTER_CARROT_GOOD_COUNT_LO = 40085
REGISTER_CARROT_GOOD_COUNT_HI = 40086
REGISTER_CARROT_BAD_COUNT_LO = 40087
REGISTER_CARROT_BAD_COUNT_HI = 40088
REGISTER_RADISH_GOOD_COUNT_LO = 40089
REGISTER_RADISH_GOOD_COUNT_HI = 40090
REGISTER_RADISH_BAD_COUNT_LO = 40091
REGISTER_RADISH_BAD_COUNT_HI = 40092
REGISTER_FARM_STATS_SEQ = 40093
REGISTER_FARM_HEARTBEAT = 40094
REGISTER_SYSTEM_RESERVED_START = 40095
REGISTER_SYSTEM_RESERVED_END = 40100

# Backward-compatible aliases for older notes/tests that used generic names.
REGISTER_SYSTEM_HEARTBEAT = REGISTER_FARM_HEARTBEAT
REGISTER_SYSTEM_MODE = REGISTER_SYSTEM_STATE
REGISTER_FARM_STATUS = REGISTER_SYSTEM_STATE

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

SYSTEM_COMMAND_NONE = 0
SYSTEM_COMMAND_HARVEST_START = 1
SYSTEM_COMMAND_PAUSE_ALL = 2
SYSTEM_COMMAND_RESUME_ALL = 3
SYSTEM_COMMAND_NAME_TO_VALUE = {
    "none": SYSTEM_COMMAND_NONE,
    "harvest_start": SYSTEM_COMMAND_HARVEST_START,
    "start_harvest": SYSTEM_COMMAND_HARVEST_START,
    "pause_all": SYSTEM_COMMAND_PAUSE_ALL,
    "system_pause": SYSTEM_COMMAND_PAUSE_ALL,
    "resume_all": SYSTEM_COMMAND_RESUME_ALL,
    "system_resume": SYSTEM_COMMAND_RESUME_ALL,
}
SYSTEM_COMMAND_VALUE_TO_NAME = {
    SYSTEM_COMMAND_NONE: "none",
    SYSTEM_COMMAND_HARVEST_START: "harvest_start",
    SYSTEM_COMMAND_PAUSE_ALL: "pause_all",
    SYSTEM_COMMAND_RESUME_ALL: "resume_all",
}

SYSTEM_STATE_IDLE = 0
SYSTEM_STATE_HARVESTING = 1
SYSTEM_STATE_PAUSED = 2
SYSTEM_STATE_ERROR = 3
SYSTEM_STATE_EMERGENCY_STOP = 4

DOBOT_COMMAND_NONE = 0
DOBOT_COMMAND_HOME = 1
DOBOT_COMMAND_MOVE_CAPTURE_POSE = 2
DOBOT_COMMAND_PICK = 3
DOBOT_COMMAND_PLACE = 4
DOBOT_COMMAND_STOP = 5
DOBOT_COMMAND_RESET = 6

DOBOT_STATUS_IDLE = 0
DOBOT_STATUS_MOVING = 1
DOBOT_STATUS_CAPTURING = 2
DOBOT_STATUS_PICKING = 3
DOBOT_STATUS_PLACING = 4
DOBOT_STATUS_PAUSED = 5
DOBOT_STATUS_ERROR = 6

QUALITY_UNKNOWN = 0
QUALITY_GOOD = 1
QUALITY_BAD = 2

TURTLEBOT_COMMAND_NONE = 0
TURTLEBOT_COMMAND_DELIVER_START = 1
TURTLEBOT_COMMAND_PAUSE = 2
TURTLEBOT_COMMAND_RESUME = 3
TURTLEBOT_COMMAND_RETURN_HOME = 4
TURTLEBOT_COMMAND_STOP = 5
TURTLEBOT_COMMAND_RESET = 6

TURTLEBOT_STATUS_IDLE = 0
TURTLEBOT_STATUS_NAVIGATING = 1
TURTLEBOT_STATUS_ARRIVED = 2
TURTLEBOT_STATUS_DELIVERING = 3
TURTLEBOT_STATUS_PAUSED = 4
TURTLEBOT_STATUS_ERROR = 5

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
    RegisterSpec(40031, "dobot_command", "orchestrator/backend", "0 none, 1 home, 2 move_capture_pose, 3 pick, 4 place, 5 stop, 6 reset"),
    RegisterSpec(40032, "dobot_target_slot", "orchestrator/backend", "harvest slot or target index"),
    RegisterSpec(40033, "dobot_command_seq", "orchestrator/backend", "incrementing command sequence"),
    RegisterSpec(40034, "dobot_command_ack_seq", "Dobot client", "last handled command sequence"),
    RegisterSpec(40035, "dobot_status", "Dobot client", "0 idle, 1 moving, 2 capturing, 3 picking, 4 placing, 5 paused, 6 error"),
    RegisterSpec(40036, "dobot_error_code", "Dobot client", "Dobot/ROS error code"),
    RegisterSpec(40037, "dobot_current_step", "Dobot client", "harvest/capture/place sequence step"),
    RegisterSpec(40038, "dobot_quality_result", "Dobot/AI client", "0 unknown, 1 good, 2 bad"),
    RegisterSpec(40039, "dobot_busy", "Dobot client", "0/1"),
    RegisterSpec(40040, "dobot_heartbeat", "Dobot client", "incrementing heartbeat"),
    RegisterSpec(40041, "dobot_last_event", "Dobot client", "last Dobot event enum"),
    RegisterSpec(40051, "turtlebot_command", "orchestrator/backend", "0 none, 1 deliver_start, 2 pause, 3 resume, 4 return_home, 5 stop, 6 reset"),
    RegisterSpec(40052, "turtlebot_target_goal", "orchestrator/backend", "delivery destination/goal index"),
    RegisterSpec(40053, "turtlebot_command_seq", "orchestrator/backend", "incrementing command sequence"),
    RegisterSpec(40054, "turtlebot_command_ack_seq", "TurtleBot client", "last handled command sequence"),
    RegisterSpec(40055, "turtlebot_status", "TurtleBot client", "0 idle, 1 navigating, 2 arrived, 3 delivering, 4 paused, 5 error"),
    RegisterSpec(40056, "turtlebot_error_code", "TurtleBot client", "navigation/ROS error code"),
    RegisterSpec(40057, "turtlebot_nav_state", "TurtleBot client", "Nav2/internal navigation state"),
    RegisterSpec(40058, "turtlebot_battery_percent", "TurtleBot client", "0~100"),
    RegisterSpec(40059, "turtlebot_current_goal", "TurtleBot client", "current goal index"),
    RegisterSpec(40060, "turtlebot_delivery_count_lo", "TurtleBot client", "device delivery count low 16 bits"),
    RegisterSpec(40061, "turtlebot_delivery_count_hi", "TurtleBot client", "device delivery count high 16 bits"),
    RegisterSpec(40062, "turtlebot_last_event", "TurtleBot client", "last TurtleBot event enum"),
    RegisterSpec(40063, "turtlebot_heartbeat", "TurtleBot client", "incrementing heartbeat"),
    RegisterSpec(40071, "system_command", "Web/backend", "0 none, 1 harvest_start, 2 pause_all, 3 resume_all"),
    RegisterSpec(40072, "system_command_seq", "Web/backend", "increment to issue a new system command"),
    RegisterSpec(40073, "system_command_ack_seq", "orchestrator/backend", "last handled system command sequence"),
    RegisterSpec(40074, "system_state", "orchestrator/backend", "0 idle, 1 harvesting, 2 paused, 3 error, 4 emergency_stop"),
    RegisterSpec(40075, "system_error_code", "orchestrator/backend", "overall system error code"),
    RegisterSpec(40076, "ai_defect_rate_bp", "AI/backend", "basis points: 0~10000 = 0.00%~100.00%"),
    RegisterSpec(40077, "total_harvest_count_lo", "backend/stat aggregator", "total harvest count low 16 bits"),
    RegisterSpec(40078, "total_harvest_count_hi", "backend/stat aggregator", "total harvest count high 16 bits"),
    RegisterSpec(40079, "turtlebot_delivery_total_lo", "backend/stat aggregator", "TurtleBot total deliveries low 16 bits"),
    RegisterSpec(40080, "turtlebot_delivery_total_hi", "backend/stat aggregator", "TurtleBot total deliveries high 16 bits"),
    RegisterSpec(40081, "tomato_good_count_lo", "backend/stat aggregator", "tomato good count low 16 bits"),
    RegisterSpec(40082, "tomato_good_count_hi", "backend/stat aggregator", "tomato good count high 16 bits"),
    RegisterSpec(40083, "tomato_bad_count_lo", "backend/stat aggregator", "tomato bad count low 16 bits"),
    RegisterSpec(40084, "tomato_bad_count_hi", "backend/stat aggregator", "tomato bad count high 16 bits"),
    RegisterSpec(40085, "carrot_good_count_lo", "backend/stat aggregator", "carrot good count low 16 bits"),
    RegisterSpec(40086, "carrot_good_count_hi", "backend/stat aggregator", "carrot good count high 16 bits"),
    RegisterSpec(40087, "carrot_bad_count_lo", "backend/stat aggregator", "carrot bad count low 16 bits"),
    RegisterSpec(40088, "carrot_bad_count_hi", "backend/stat aggregator", "carrot bad count high 16 bits"),
    RegisterSpec(40089, "radish_good_count_lo", "backend/stat aggregator", "radish good count low 16 bits"),
    RegisterSpec(40090, "radish_good_count_hi", "backend/stat aggregator", "radish good count high 16 bits"),
    RegisterSpec(40091, "radish_bad_count_lo", "backend/stat aggregator", "radish bad count low 16 bits"),
    RegisterSpec(40092, "radish_bad_count_hi", "backend/stat aggregator", "radish bad count high 16 bits"),
    RegisterSpec(40093, "farm_stats_seq", "backend/stat aggregator", "incrementing stats update sequence"),
    RegisterSpec(40094, "farm_heartbeat", "backend/stat aggregator", "farm stats heartbeat"),
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


def split_u32(value: int) -> Tuple[int, int]:
    """Split an unsigned 32-bit value into little-endian Modbus word pair.

    Returns ``(lo, hi)`` so adjacent registers can be documented naturally as
    ``*_lo`` then ``*_hi``.
    """
    value = int(value)
    if not 0 <= value <= U32_MAX:
        raise ValueError(f"u32 value out of range: {value}")
    return value & U16_MAX, (value >> 16) & U16_MAX


def combine_u32(lo: int, hi: int) -> int:
    """Combine ``*_lo`` and ``*_hi`` Modbus words into an unsigned 32-bit int."""
    lo = int(lo)
    hi = int(hi)
    if not 0 <= lo <= U16_MAX:
        raise ValueError(f"lo word out of range: {lo}")
    if not 0 <= hi <= U16_MAX:
        raise ValueError(f"hi word out of range: {hi}")
    return (hi << 16) | lo


def parse_system_command(command: object) -> int:
    """Parse a system command string/int to the Modbus enum value."""
    if isinstance(command, int):
        if command in SYSTEM_COMMAND_VALUE_TO_NAME:
            return command
        raise ValueError(f"Unsupported system command value: {command}")
    normalized = str(command).strip().lower().replace("-", "_")
    if normalized in SYSTEM_COMMAND_NAME_TO_VALUE:
        return SYSTEM_COMMAND_NAME_TO_VALUE[normalized]
    raise ValueError(f"Unsupported system command: {command}")


def system_command_name(command_value: int) -> str:
    return SYSTEM_COMMAND_VALUE_TO_NAME.get(int(command_value), f"unknown({command_value})")


def initial_holding_registers(count: int = SERVER_HR_COUNT) -> List[int]:
    """Return initial holding-register values sized for 40001..40100."""
    values = [0] * int(count)
    # Safe conveyor defaults.
    values[protocol_address(REGISTER_CONVEYOR_COMMAND)] = COMMAND_STOP
    values[protocol_address(REGISTER_CONVEYOR_SPEED_CMD)] = 0
    values[protocol_address(REGISTER_CONVEYOR_STATUS)] = STATUS_IDLE
    values[protocol_address(REGISTER_CONVEYOR_ERROR_CODE)] = ERROR_NONE
    # Safe system/device defaults.
    values[protocol_address(REGISTER_SYSTEM_COMMAND)] = SYSTEM_COMMAND_NONE
    values[protocol_address(REGISTER_SYSTEM_STATE)] = SYSTEM_STATE_IDLE
    values[protocol_address(REGISTER_DOBOT_COMMAND)] = DOBOT_COMMAND_NONE
    values[protocol_address(REGISTER_DOBOT_STATUS)] = DOBOT_STATUS_IDLE
    values[protocol_address(REGISTER_TURTLEBOT_COMMAND)] = TURTLEBOT_COMMAND_NONE
    values[protocol_address(REGISTER_TURTLEBOT_STATUS)] = TURTLEBOT_STATUS_IDLE
    return values


def markdown_register_table() -> str:
    lines = ["| Register | Address | Name | Owner | Notes |", "|---:|---:|---|---|---|"]
    for spec in REGISTER_SPECS:
        lines.append(
            f"| {spec.register} | {protocol_address(spec.register)} | `{spec.name}` | {spec.owner} | {spec.description} |"
        )
    return "\n".join(lines)

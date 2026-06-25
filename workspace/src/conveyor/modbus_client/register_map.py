"""Register map for the SmartFarmProject conveyor Modbus block.

Human-facing holding register numbers use the usual 4xxxx notation.  Pymodbus
uses zero-based protocol addresses, so 40021 maps to address 20.
"""

from __future__ import annotations

from typing import Dict

HOLDING_REGISTER_BASE = 40001
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

CONVEYOR_REGISTER_START = REGISTER_CONVEYOR_COMMAND
CONVEYOR_REGISTER_END = REGISTER_CONVEYOR_RESERVED_3
CONVEYOR_BLOCK_COUNT = CONVEYOR_REGISTER_END - CONVEYOR_REGISTER_START + 1
CONVEYOR_BLOCK_START_ADDRESS = REGISTER_CONVEYOR_COMMAND - HOLDING_REGISTER_BASE

COMMAND_STOP = 0
COMMAND_RUN_CLOCKWISE = 1
COMMAND_RUN_COUNTER_CLOCKWISE = 2
COMMAND_RESET = 3
COMMAND_EMERGENCY_STOP = 4

COMMAND_NAME_TO_VALUE: Dict[str, int] = {
    "stop": COMMAND_STOP,
    "run_clockwise": COMMAND_RUN_CLOCKWISE,
    "cw": COMMAND_RUN_CLOCKWISE,
    "run_cw": COMMAND_RUN_CLOCKWISE,
    "run_counter_clockwise": COMMAND_RUN_COUNTER_CLOCKWISE,
    "ccw": COMMAND_RUN_COUNTER_CLOCKWISE,
    "run_ccw": COMMAND_RUN_COUNTER_CLOCKWISE,
    "reset": COMMAND_RESET,
    "emergency_stop": COMMAND_EMERGENCY_STOP,
    "estop": COMMAND_EMERGENCY_STOP,
    "e_stop": COMMAND_EMERGENCY_STOP,
}
COMMAND_VALUE_TO_NAME = {value: name for name, value in COMMAND_NAME_TO_VALUE.items() if name in {
    "stop",
    "run_clockwise",
    "run_counter_clockwise",
    "reset",
    "emergency_stop",
}}

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


def protocol_address(register_number: int) -> int:
    """Convert a 40021~40030 register number to a pymodbus address."""
    register_number = int(register_number)
    if not CONVEYOR_REGISTER_START <= register_number <= CONVEYOR_REGISTER_END:
        raise ValueError(
            f"Register {register_number} is outside conveyor block "
            f"{CONVEYOR_REGISTER_START}~{CONVEYOR_REGISTER_END}"
        )
    return register_number - HOLDING_REGISTER_BASE


def parse_command(command: object) -> int:
    """Parse an int/string command into the conveyor command enum."""
    if isinstance(command, int):
        if command in COMMAND_VALUE_TO_NAME:
            return command
        raise ValueError(f"Unsupported conveyor command value: {command}")
    normalized = str(command).strip().lower().replace("-", "_")
    if normalized in COMMAND_NAME_TO_VALUE:
        return COMMAND_NAME_TO_VALUE[normalized]
    raise ValueError(f"Unsupported conveyor command: {command}")


def command_name(command: int) -> str:
    return COMMAND_VALUE_TO_NAME.get(int(command), f"unknown({command})")

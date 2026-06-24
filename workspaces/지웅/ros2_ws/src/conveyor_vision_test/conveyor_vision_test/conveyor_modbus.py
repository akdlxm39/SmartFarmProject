"""Modbus TCP helpers for SmartFarmProject conveyor control.

Register numbers are documented in the usual holding-register notation
(40021, 40022, ...). Pymodbus normally expects zero-based protocol addresses,
so 40021 is written as address 20 by default.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

ColorDetection = Dict[str, object]

# Holding register numbers agreed for the conveyor block.
# Conveyor uses 40021~40030, which correspond to pymodbus addresses 20~29.
# The current implementation writes 40021~40027; 40028~40030 are reserved.
MODBUS_HOLDING_REGISTER_BASE = 40001
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

CONVEYOR_REGISTERS = {
    "conveyor_command": REGISTER_CONVEYOR_COMMAND,
    "conveyor_speed_cmd": REGISTER_CONVEYOR_SPEED_CMD,
    "conveyor_status": REGISTER_CONVEYOR_STATUS,
    "conveyor_error_code": REGISTER_CONVEYOR_ERROR_CODE,
    "cube_detected": REGISTER_CUBE_DETECTED,
    "cube_color": REGISTER_CUBE_COLOR,
    "last_vision_event": REGISTER_LAST_VISION_EVENT,
}

# 40021 conveyor_command
COMMAND_STOP = 0
COMMAND_RUN_CLOCKWISE = 1
COMMAND_RUN_COUNTER_CLOCKWISE = 2
COMMAND_RESET = 3
COMMAND_EMERGENCY_STOP = 4

COMMAND_NAME_TO_VALUE = {
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
COMMAND_VALUE_TO_NAME = {
    COMMAND_STOP: "stop",
    COMMAND_RUN_CLOCKWISE: "run_clockwise",
    COMMAND_RUN_COUNTER_CLOCKWISE: "run_counter_clockwise",
    COMMAND_RESET: "reset",
    COMMAND_EMERGENCY_STOP: "emergency_stop",
}

# 40023 conveyor_status
STATUS_IDLE = 0
STATUS_RUNNING = 1
STATUS_DELIVERED = 2
STATUS_ERROR = 3
STATUS_EMERGENCY_STOPPED = 4

# 40026 cube_color
COLOR_NONE = 0
COLOR_RED = 1
COLOR_GREEN = 2
COLOR_UNKNOWN = 3

# 40027 last_vision_event
EVENT_NONE = 0
EVENT_CUBE_DETECTED = 1
EVENT_CUBE_LOST = 2
EVENT_DELIVERED = 3
EVENT_ERROR = 4
EVENT_EMERGENCY_STOP = 5

ERROR_NONE = 0
ERROR_MODBUS_WRITE_FAILED = 1
ERROR_INVALID_COMMAND = 2


def register_to_pymodbus_address(register_number: int, zero_based: bool = True) -> int:
    """Convert 4xxxx-style register number to pymodbus protocol address."""
    if zero_based:
        return register_number - MODBUS_HOLDING_REGISTER_BASE
    return register_number


def parse_conveyor_command(command: object) -> int:
    """Parse command string/int to the conveyor_command enum value."""
    if isinstance(command, int):
        if command in COMMAND_VALUE_TO_NAME:
            return command
        raise ValueError(f"Unsupported conveyor command value: {command}")

    normalized = str(command).strip().lower().replace("-", "_")
    if normalized in COMMAND_NAME_TO_VALUE:
        return COMMAND_NAME_TO_VALUE[normalized]
    raise ValueError(f"Unsupported conveyor command: {command}")


def command_name(command_value: int) -> str:
    return COMMAND_VALUE_TO_NAME.get(command_value, f"unknown({command_value})")


def color_code_from_detections(detections: Sequence[ColorDetection]) -> int:
    """Return color enum for the current detections.

    If both red and green are visible at the same time, return unknown because the
    register is a single value. The detector still draws every bounding box.
    """
    colors = {str(item.get("color", "")).lower() for item in detections}
    colors.discard("")
    if not colors:
        return COLOR_NONE
    if colors == {"red"}:
        return COLOR_RED
    if colors == {"green"}:
        return COLOR_GREEN
    return COLOR_UNKNOWN


@dataclass(frozen=True)
class ConveyorRegisterState:
    """Desired conveyor command plus PC-owned vision register snapshot."""

    conveyor_command: int
    conveyor_speed_cmd: int
    conveyor_status: int
    conveyor_error_code: int
    cube_detected: int
    cube_color: int
    last_vision_event: int

    def as_register_values(self) -> List[int]:
        return [
            int(self.conveyor_command),
            int(self.conveyor_speed_cmd),
            int(self.conveyor_status),
            int(self.conveyor_error_code),
            int(self.cube_detected),
            int(self.cube_color),
            int(self.last_vision_event),
        ]

    def as_register_dict(self) -> Dict[int, int]:
        return dict(zip(CONVEYOR_REGISTERS.values(), self.as_register_values()))


@dataclass(frozen=True)
class ConveyorPhysicalState:
    """Pi-owned physical conveyor status read from 40023~40024."""

    conveyor_status: int
    conveyor_error_code: int


@dataclass(frozen=True)
class ConveyorCommandWritePlan:
    """Modbus writes the ROS vision node is allowed to submit this cycle.

    `command` and `speed_cmd` are optional because safety gating may suppress
    motion commands while still allowing the node to publish PC-owned vision
    registers (40025~40027).
    """

    command: Optional[int]
    speed_cmd: Optional[int]
    cube_detected: int
    cube_color: int
    last_vision_event: int
    skip_reason: str = ""

    @property
    def command_values(self) -> Optional[List[int]]:
        if self.command is None or self.speed_cmd is None:
            return None
        return [int(self.command), int(self.speed_cmd)]

    @property
    def vision_values(self) -> List[int]:
        return [
            int(self.cube_detected),
            int(self.cube_color),
            int(self.last_vision_event),
        ]


def _command_allowed_for_physical_status(command: int, physical_state: ConveyorPhysicalState) -> Tuple[bool, str]:
    status = int(physical_state.conveyor_status)
    if status == STATUS_EMERGENCY_STOPPED:
        return False, "blocked: conveyor is emergency_stopped; command register is not written"

    if command in {COMMAND_RUN_CLOCKWISE, COMMAND_RUN_COUNTER_CLOCKWISE, COMMAND_RESET}:
        if status in {STATUS_IDLE, STATUS_RUNNING, STATUS_DELIVERED}:
            return True, ""
        if status == STATUS_ERROR:
            return False, "blocked: conveyor status is error; run/reset commands require manual recovery"
        return False, f"blocked: unsupported conveyor status {status} for motion command"

    if command == COMMAND_STOP:
        if status in {STATUS_IDLE, STATUS_RUNNING, STATUS_DELIVERED, STATUS_ERROR}:
            return True, ""
        return False, f"blocked: unsupported conveyor status {status} for stop command"

    if command == COMMAND_EMERGENCY_STOP:
        if status == STATUS_EMERGENCY_STOPPED:
            return False, "blocked: conveyor is already emergency_stopped"
        return True, ""

    return False, f"blocked: unsupported command {command}"


def build_command_write_plan(
    desired_state: ConveyorRegisterState,
    physical_state: Optional[ConveyorPhysicalState],
) -> ConveyorCommandWritePlan:
    """Gate desired vision-triggered commands using the Pi-owned status.

    Policy:
    - emergency_stopped: write no command/speed at all; only vision registers.
    - error: never issue motion/reset from vision; allow `stop` only.
    - idle/running/delivered: allow run/stop commands generated by the ROI state machine.
    - unreadable status: fail safe and write only vision registers.
    """
    if physical_state is None:
        return ConveyorCommandWritePlan(
            command=None,
            speed_cmd=None,
            cube_detected=desired_state.cube_detected,
            cube_color=desired_state.cube_color,
            last_vision_event=desired_state.last_vision_event,
            skip_reason="blocked: physical status could not be read",
        )

    allowed, reason = _command_allowed_for_physical_status(
        desired_state.conveyor_command,
        physical_state,
    )
    return ConveyorCommandWritePlan(
        command=desired_state.conveyor_command if allowed else None,
        speed_cmd=desired_state.conveyor_speed_cmd if allowed else None,
        cube_detected=desired_state.cube_detected,
        cube_color=desired_state.cube_color,
        last_vision_event=desired_state.last_vision_event,
        skip_reason=reason,
    )


class ConveyorVisionStateMachine:
    """Convert ROI detections to conveyor Modbus register states."""

    def __init__(
        self,
        disappear_stable_frames: int = 10,
        run_command: int = COMMAND_RUN_CLOCKWISE,
        speed_cmd: int = 100,
    ) -> None:
        if disappear_stable_frames < 1:
            raise ValueError("disappear_stable_frames must be >= 1")
        self.disappear_stable_frames = int(disappear_stable_frames)
        self.run_command = parse_conveyor_command(run_command)
        self.speed_cmd = int(speed_cmd)
        self.object_active = False
        self.no_detection_streak = 0

    def idle_state(self) -> ConveyorRegisterState:
        return ConveyorRegisterState(
            conveyor_command=COMMAND_STOP,
            conveyor_speed_cmd=self.speed_cmd,
            conveyor_status=STATUS_IDLE,
            conveyor_error_code=ERROR_NONE,
            cube_detected=0,
            cube_color=COLOR_NONE,
            last_vision_event=EVENT_NONE,
        )

    def emergency_stop_state(self) -> ConveyorRegisterState:
        self.object_active = False
        self.no_detection_streak = 0
        return ConveyorRegisterState(
            conveyor_command=COMMAND_EMERGENCY_STOP,
            conveyor_speed_cmd=0,
            conveyor_status=STATUS_EMERGENCY_STOPPED,
            conveyor_error_code=ERROR_NONE,
            cube_detected=0,
            cube_color=COLOR_NONE,
            last_vision_event=EVENT_EMERGENCY_STOP,
        )

    def update(self, detections: Sequence[ColorDetection]) -> ConveyorRegisterState:
        cube_detected = bool(detections)
        if cube_detected:
            self.object_active = True
            self.no_detection_streak = 0
            return ConveyorRegisterState(
                conveyor_command=self.run_command,
                conveyor_speed_cmd=self.speed_cmd,
                conveyor_status=STATUS_RUNNING,
                conveyor_error_code=ERROR_NONE,
                cube_detected=1,
                cube_color=color_code_from_detections(detections),
                last_vision_event=EVENT_CUBE_DETECTED,
            )

        if self.object_active:
            self.no_detection_streak += 1
            if self.no_detection_streak >= self.disappear_stable_frames:
                self.object_active = False
                self.no_detection_streak = 0
                return ConveyorRegisterState(
                    conveyor_command=COMMAND_STOP,
                    conveyor_speed_cmd=self.speed_cmd,
                    conveyor_status=STATUS_DELIVERED,
                    conveyor_error_code=ERROR_NONE,
                    cube_detected=0,
                    cube_color=COLOR_NONE,
                    last_vision_event=EVENT_DELIVERED,
                )
            return ConveyorRegisterState(
                conveyor_command=self.run_command,
                conveyor_speed_cmd=self.speed_cmd,
                conveyor_status=STATUS_RUNNING,
                conveyor_error_code=ERROR_NONE,
                cube_detected=0,
                cube_color=COLOR_NONE,
                last_vision_event=EVENT_CUBE_LOST,
            )

        return self.idle_state()


class ConveyorModbusTcpClient:
    """Small wrapper around pymodbus for writing the conveyor register block."""

    def __init__(
        self,
        host: str = "192.168.110.109",
        port: int = 50200,
        unit_id: int = 1,
        timeout: float = 1.0,
        zero_based_addresses: bool = True,
        dry_run: bool = False,
        client_factory: Optional[Callable[..., object]] = None,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.unit_id = int(unit_id)
        self.timeout = float(timeout)
        self.zero_based_addresses = bool(zero_based_addresses)
        self.dry_run = bool(dry_run)
        self.client_factory = client_factory
        self.client: Optional[object] = None

    def _make_client(self) -> object:
        if self.client_factory is not None:
            return self.client_factory(host=self.host, port=self.port, timeout=self.timeout)
        try:
            from pymodbus.client import ModbusTcpClient  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "pymodbus is not installed for /usr/bin/python3. Install with: "
                "/usr/bin/python3 -m pip install --user pymodbus==3.13.1"
            ) from exc
        return ModbusTcpClient(self.host, port=self.port, timeout=self.timeout)

    def connect(self) -> bool:
        if self.dry_run:
            return True
        if self.client is None:
            self.client = self._make_client()
        connect = getattr(self.client, "connect", None)
        if connect is None:
            return True
        return bool(connect())

    def close(self) -> None:
        if self.client is None:
            return
        close = getattr(self.client, "close", None)
        if close is not None:
            close()
        self.client = None

    def _write_registers_call(self, start_address: int, values: Sequence[int]) -> object:
        if self.client is None:
            raise RuntimeError("Modbus client is not connected")
        write_registers = getattr(self.client, "write_registers")
        for unit_kw in ("device_id", "slave", "unit"):
            try:
                return write_registers(
                    start_address,
                    list(values),
                    **{unit_kw: self.unit_id},
                )
            except TypeError:
                continue
        return write_registers(start_address, list(values))

    def _write_register_call(self, address: int, value: int) -> object:
        if self.client is None:
            raise RuntimeError("Modbus client is not connected")
        write_register = getattr(self.client, "write_register")
        for unit_kw in ("device_id", "slave", "unit"):
            try:
                return write_register(address, int(value), **{unit_kw: self.unit_id})
            except TypeError:
                continue
        return write_register(address, int(value))

    def _read_holding_registers_call(self, start_address: int, count: int) -> object:
        if self.client is None:
            raise RuntimeError("Modbus client is not connected")
        read_holding_registers = getattr(self.client, "read_holding_registers")
        for unit_kw in ("device_id", "slave", "unit"):
            try:
                return read_holding_registers(
                    start_address,
                    count=count,
                    **{unit_kw: self.unit_id},
                )
            except TypeError:
                continue
        return read_holding_registers(start_address, count=count)

    @staticmethod
    def _is_error(result: object) -> bool:
        is_error = getattr(result, "isError", None)
        if is_error is None:
            return False
        return bool(is_error())

    def write_state(self, state: ConveyorRegisterState) -> bool:
        """Legacy contiguous 40021~40027 writer.

        Kept for manual smoke tests. The ROS detector should prefer
        `write_vision_command_state()` so it does not overwrite Pi-owned
        physical status/error registers.
        """
        values = state.as_register_values()
        if self.dry_run:
            return True
        if not self.connect():
            return False

        start_address = register_to_pymodbus_address(
            REGISTER_CONVEYOR_COMMAND,
            zero_based=self.zero_based_addresses,
        )
        result = self._write_registers_call(start_address, values)
        return not self._is_error(result)

    def read_physical_state(self) -> Optional[ConveyorPhysicalState]:
        """Read Pi-owned conveyor status/error from 40023~40024."""
        if self.dry_run:
            return ConveyorPhysicalState(
                conveyor_status=STATUS_IDLE,
                conveyor_error_code=ERROR_NONE,
            )
        if not self.connect():
            return None

        start_address = register_to_pymodbus_address(
            REGISTER_CONVEYOR_STATUS,
            zero_based=self.zero_based_addresses,
        )
        result = self._read_holding_registers_call(start_address, count=2)
        if self._is_error(result):
            return None
        registers = getattr(result, "registers", None)
        if registers is None or len(registers) < 2:
            return None
        return ConveyorPhysicalState(
            conveyor_status=int(registers[0]),
            conveyor_error_code=int(registers[1]),
        )

    def write_command_plan(self, plan: ConveyorCommandWritePlan) -> bool:
        """Write allowed command/speed plus PC-owned vision registers.

        This deliberately does not write 40023/40024 because the Raspberry Pi
        controller owns physical status and error reporting.
        """
        if self.dry_run:
            return True
        if not self.connect():
            return False

        ok = True
        command_values = plan.command_values
        if command_values is not None:
            command_address = register_to_pymodbus_address(
                REGISTER_CONVEYOR_COMMAND,
                zero_based=self.zero_based_addresses,
            )
            command_result = self._write_registers_call(command_address, command_values)
            ok = ok and not self._is_error(command_result)

        vision_address = register_to_pymodbus_address(
            REGISTER_CUBE_DETECTED,
            zero_based=self.zero_based_addresses,
        )
        vision_result = self._write_registers_call(vision_address, plan.vision_values)
        return ok and not self._is_error(vision_result)

    def write_vision_command_state(self, desired_state: ConveyorRegisterState) -> bool:
        """Read status, gate command, then write command/vision registers."""
        physical_state = self.read_physical_state()
        plan = build_command_write_plan(desired_state, physical_state)
        return self.write_command_plan(plan)

    def write_command(self, command: object, speed_cmd: int = 0) -> bool:
        """Write a manual command to 40021 and speed to 40022."""
        command_value = parse_conveyor_command(command)
        if self.dry_run:
            return True
        if not self.connect():
            return False

        command_address = register_to_pymodbus_address(
            REGISTER_CONVEYOR_COMMAND,
            zero_based=self.zero_based_addresses,
        )
        speed_address = register_to_pymodbus_address(
            REGISTER_CONVEYOR_SPEED_CMD,
            zero_based=self.zero_based_addresses,
        )
        result_1 = self._write_register_call(command_address, command_value)
        result_2 = self._write_register_call(speed_address, int(speed_cmd))
        return not self._is_error(result_1) and not self._is_error(result_2)


def format_register_state(state: ConveyorRegisterState) -> str:
    pairs = [
        f"40021 command={state.conveyor_command}({command_name(state.conveyor_command)})",
        f"40022 speed={state.conveyor_speed_cmd}",
        f"40023 status={state.conveyor_status}",
        f"40024 error={state.conveyor_error_code}",
        f"40025 detected={state.cube_detected}",
        f"40026 color={state.cube_color}",
        f"40027 event={state.last_vision_event}",
    ]
    return ", ".join(pairs)

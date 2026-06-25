#!/usr/bin/env python3
"""Raspberry Pi Modbus client + GPIO conveyor controller.

The Modbus server is external (default: 192.168.110.109:50200). This process is a
client: it reads command/speed registers and writes real motor status/error
registers. Local emergency/restart buttons update status/error only; they do not
rewrite the command register.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import logging
from dataclasses import dataclass
from typing import Optional, Sequence

from conveyor_motor import ButtonReader, ConveyorMotor
from register_map import (
    COMMAND_EMERGENCY_STOP,
    COMMAND_RESET,
    COMMAND_RUN_CLOCKWISE,
    COMMAND_RUN_COUNTER_CLOCKWISE,
    COMMAND_STOP,
    CONVEYOR_BLOCK_COUNT,
    CONVEYOR_BLOCK_START_ADDRESS,
    ERROR_INVALID_COMMAND,
    ERROR_LOCAL_EMERGENCY_STOP,
    ERROR_MODBUS_CONNECT_FAILED,
    ERROR_MODBUS_READ_FAILED,
    ERROR_MODBUS_WRITE_FAILED,
    ERROR_NONE,
    REGISTER_CONVEYOR_ERROR_CODE,
    REGISTER_CONVEYOR_STATUS,
    STATUS_EMERGENCY_STOPPED,
    STATUS_ERROR,
    STATUS_IDLE,
    STATUS_RUNNING,
    command_name,
    parse_command,
    protocol_address,
)

LOG = logging.getLogger("conveyor_pi_controller")


@dataclass(frozen=True)
class ControllerState:
    status: int
    error_code: int
    write_command: Optional[int] = None


class ConveyorController:
    """Pure controller state machine around a motor object."""

    def __init__(self, motor: ConveyorMotor) -> None:
        self.motor = motor
        self.local_emergency_latched = False
        self.last_command: Optional[int] = None
        self.last_speed_cmd: Optional[int] = None
        self.state = ControllerState(STATUS_IDLE, ERROR_NONE)

    def _set_state(self, status: int, error_code: int) -> ControllerState:
        self.state = ControllerState(status=status, error_code=error_code, write_command=None)
        return self.state

    def apply_modbus_command(self, command: object, speed_cmd: int = 0) -> ControllerState:
        try:
            command_value = parse_command(command)
        except ValueError:
            self.motor.stop()
            return self._set_state(STATUS_ERROR, ERROR_INVALID_COMMAND)

        if self.local_emergency_latched:
            return self._set_state(STATUS_EMERGENCY_STOPPED, ERROR_LOCAL_EMERGENCY_STOP)

        speed_cmd = int(speed_cmd)
        changed = command_value != self.last_command or speed_cmd != self.last_speed_cmd
        self.last_command = command_value
        self.last_speed_cmd = speed_cmd

        if command_value == COMMAND_STOP:
            if changed:
                self.motor.stop()
            return self._set_state(STATUS_IDLE, ERROR_NONE)

        if command_value == COMMAND_RUN_CLOCKWISE:
            if changed or not bool(getattr(self.motor, "running", False)):
                self.motor.start_clockwise(speed_cmd)
            return self._set_state(STATUS_RUNNING, ERROR_NONE)

        if command_value == COMMAND_RUN_COUNTER_CLOCKWISE:
            if changed or not bool(getattr(self.motor, "running", False)):
                self.motor.start_counter_clockwise(speed_cmd)
            return self._set_state(STATUS_RUNNING, ERROR_NONE)

        if command_value == COMMAND_RESET:
            if changed:
                self.motor.stop()
            return self._set_state(STATUS_IDLE, ERROR_NONE)

        if command_value == COMMAND_EMERGENCY_STOP:
            if changed:
                self.motor.emergency_stop()
            return self._set_state(STATUS_EMERGENCY_STOPPED, ERROR_LOCAL_EMERGENCY_STOP)

        self.motor.stop()
        return self._set_state(STATUS_ERROR, ERROR_INVALID_COMMAND)

    def handle_emergency_button(self) -> ControllerState:
        self.local_emergency_latched = True
        self.motor.emergency_stop()
        # Per project decision: local buttons do NOT rewrite 40021 command register.
        return self._set_state(STATUS_EMERGENCY_STOPPED, ERROR_LOCAL_EMERGENCY_STOP)

    def handle_restart_button(self) -> ControllerState:
        self.local_emergency_latched = False
        self.last_command = None
        self.last_speed_cmd = None
        self.motor.stop()
        # Safety policy: restart clears the latch only; it never starts motion directly.
        return self._set_state(STATUS_IDLE, ERROR_NONE)


class DryRunModbusClient:
    """Small in-memory pymodbus-like client for local logic smoke tests."""

    def __init__(self) -> None:
        self.registers = [0] * CONVEYOR_BLOCK_COUNT
        self.connected = False

    async def connect(self) -> bool:
        self.connected = True
        return True

    async def read_holding_registers(self, address: int, *, count: int, device_id: int = 1):
        start = address - CONVEYOR_BLOCK_START_ADDRESS
        values = self.registers[start : start + count]
        return _DryRunResult(values)

    async def write_registers(self, address: int, values: Sequence[int], *, device_id: int = 1):
        start = address - CONVEYOR_BLOCK_START_ADDRESS
        for index, value in enumerate(values):
            absolute = start + index
            if 0 <= absolute < len(self.registers):
                self.registers[absolute] = int(value)
        return _DryRunResult([])

    def close(self) -> None:
        self.connected = False


class _DryRunResult:
    def __init__(self, registers: Sequence[int]) -> None:
        self.registers = list(registers)

    def isError(self) -> bool:  # pymodbus compatibility
        return False


async def maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


class ConveyorModbusClientRunner:
    def __init__(
        self,
        controller: ConveyorController,
        button_reader: Optional[ButtonReader],
        server_host: str = "192.168.110.109",
        server_port: int = 50200,
        device_id: int = 1,
        timeout: float = 1.0,
        poll_interval_sec: float = 0.05,
        reconnect_delay_sec: float = 1.0,
        dry_run_modbus: bool = False,
    ) -> None:
        self.controller = controller
        self.button_reader = button_reader
        self.server_host = server_host
        self.server_port = int(server_port)
        self.device_id = int(device_id)
        self.timeout = float(timeout)
        self.poll_interval_sec = float(poll_interval_sec)
        self.reconnect_delay_sec = float(reconnect_delay_sec)
        self.dry_run_modbus = bool(dry_run_modbus)
        self.last_written_state: Optional[ControllerState] = None

    def _make_client(self):
        if self.dry_run_modbus:
            return DryRunModbusClient()
        from pymodbus.client import AsyncModbusTcpClient  # type: ignore

        return AsyncModbusTcpClient(self.server_host, port=self.server_port, timeout=self.timeout)

    async def _connect(self, client) -> bool:
        ok = await maybe_await(client.connect())
        return bool(ok)

    @staticmethod
    def _is_error(result: object) -> bool:
        is_error = getattr(result, "isError", None)
        return bool(is_error()) if is_error is not None else False

    async def _read_command_block(self, client) -> tuple[int, int]:
        result = await client.read_holding_registers(
            CONVEYOR_BLOCK_START_ADDRESS,
            count=CONVEYOR_BLOCK_COUNT,
            device_id=self.device_id,
        )
        if self._is_error(result):
            raise RuntimeError("Modbus read returned error")
        registers = list(result.registers)
        command = int(registers[0]) if len(registers) > 0 else COMMAND_STOP
        speed_cmd = int(registers[1]) if len(registers) > 1 else 0
        return command, speed_cmd

    async def _write_status_if_changed(self, client, state: ControllerState, force: bool = False) -> None:
        if not force and state == self.last_written_state:
            return
        start = protocol_address(REGISTER_CONVEYOR_STATUS)
        result = await client.write_registers(
            start,
            [int(state.status), int(state.error_code)],
            device_id=self.device_id,
        )
        if self._is_error(result):
            raise RuntimeError("Modbus status write returned error")
        self.last_written_state = state
        LOG.info("wrote status=%s error=%s", state.status, state.error_code)

    async def run_forever(self) -> None:
        while True:
            client = self._make_client()
            try:
                if not await self._connect(client):
                    LOG.error("failed to connect to Modbus server %s:%s", self.server_host, self.server_port)
                    await asyncio.sleep(self.reconnect_delay_sec)
                    continue
                LOG.info("connected to Modbus server %s:%s", self.server_host, self.server_port)
                await self._write_status_if_changed(client, self.controller.state, force=True)

                while True:
                    if self.button_reader is not None:
                        events = self.button_reader.poll()
                        if events.emergency_pressed:
                            LOG.warning("local emergency button pressed")
                            await self._write_status_if_changed(client, self.controller.handle_emergency_button(), force=True)
                        if events.restart_pressed:
                            LOG.warning("local restart button pressed")
                            await self._write_status_if_changed(client, self.controller.handle_restart_button(), force=True)

                    command, speed_cmd = await self._read_command_block(client)
                    state = self.controller.apply_modbus_command(command, speed_cmd)
                    await self._write_status_if_changed(client, state)
                    await asyncio.sleep(self.poll_interval_sec)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                LOG.exception("controller loop error: %s", exc)
                self.controller.motor.emergency_stop()
                self.controller.state = ControllerState(STATUS_ERROR, ERROR_MODBUS_READ_FAILED)
                await asyncio.sleep(self.reconnect_delay_sec)
            finally:
                close = getattr(client, "close", None)
                if close is not None:
                    await maybe_await(close())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Raspberry Pi conveyor Modbus client + GPIO controller")
    parser.add_argument("--server-host", default="192.168.110.109")
    parser.add_argument("--server-port", type=int, default=50200)
    parser.add_argument("--device-id", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--poll-interval-sec", type=float, default=0.05)
    parser.add_argument("--reconnect-delay-sec", type=float, default=1.0)
    parser.add_argument("--gpio-chip", default="gpiochip0")
    parser.add_argument("--dry-run-motor", action="store_true", help="Do not import/use GPIO; log motor actions only")
    parser.add_argument("--dry-run-modbus", action="store_true", help="Use in-memory Modbus registers for local smoke tests")
    parser.add_argument("--log-level", default="INFO")
    return parser


async def async_main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    motor = ConveyorMotor(dry_run=args.dry_run_motor, gpio_chip=args.gpio_chip)
    button_reader = ButtonReader(dry_run=args.dry_run_motor, gpio_chip=args.gpio_chip)
    controller = ConveyorController(motor=motor)
    runner = ConveyorModbusClientRunner(
        controller=controller,
        button_reader=button_reader,
        server_host=args.server_host,
        server_port=args.server_port,
        device_id=args.device_id,
        timeout=args.timeout,
        poll_interval_sec=args.poll_interval_sec,
        reconnect_delay_sec=args.reconnect_delay_sec,
        dry_run_modbus=args.dry_run_modbus,
    )
    try:
        await runner.run_forever()
    except KeyboardInterrupt:
        LOG.info("keyboard interrupt; stopping motor")
    finally:
        motor.emergency_stop()
        button_reader.close()
        motor.close()
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())

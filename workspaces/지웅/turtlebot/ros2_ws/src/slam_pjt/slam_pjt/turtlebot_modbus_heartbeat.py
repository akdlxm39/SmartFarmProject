#!/usr/bin/env python3
"""TurtleBot Modbus heartbeat/status smoke client.

Writes the SmartFarmProject TurtleBot register block:
- 40055 turtlebot_status
- 40057 turtlebot_nav_state
- 40058 turtlebot_battery_percent
- 40059 turtlebot_current_goal
- 40063 turtlebot_heartbeat

Default addressing follows pymodbus zero-based holding register convention:
40051 -> address 50.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from typing import Iterable, Optional

STATUS_IDLE = 0
NAV_STATE_UNKNOWN = 0
CURRENT_GOAL_NONE = 0

REG_TURTLEBOT_STATUS = 40055
REG_TURTLEBOT_NAV_STATE = 40057
REG_TURTLEBOT_BATTERY_PERCENT = 40058
REG_TURTLEBOT_CURRENT_GOAL = 40059
REG_TURTLEBOT_HEARTBEAT = 40063


def to_protocol_address(register: int, zero_based: bool = True) -> int:
    """Convert literal holding register number to pymodbus protocol address."""
    if zero_based:
        return register - 40001
    return register


@dataclass
class TurtleBotStatusSnapshot:
    status: int = STATUS_IDLE
    nav_state: int = NAV_STATE_UNKNOWN
    battery_percent: int = 0
    current_goal: int = CURRENT_GOAL_NONE
    heartbeat: int = 0

    def register_values(self) -> list[tuple[int, int]]:
        return [
            (REG_TURTLEBOT_STATUS, self.status),
            (REG_TURTLEBOT_NAV_STATE, self.nav_state),
            (REG_TURTLEBOT_BATTERY_PERCENT, self.battery_percent),
            (REG_TURTLEBOT_CURRENT_GOAL, self.current_goal),
            (REG_TURTLEBOT_HEARTBEAT, self.heartbeat),
        ]


class ModbusRegisterWriter:
    def __init__(self, host: str, port: int, unit_id: int, zero_based: bool, dry_run: bool):
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.zero_based = zero_based
        self.dry_run = dry_run
        self._client = None

    def __enter__(self):
        if self.dry_run:
            return self
        try:
            from pymodbus.client import ModbusTcpClient
        except Exception as exc:  # pragma: no cover - depends on runtime env
            raise RuntimeError("pymodbus is required for non-dry-run writes") from exc
        self._client = ModbusTcpClient(self.host, port=self.port)
        if not self._client.connect():
            raise RuntimeError(f"failed to connect Modbus server {self.host}:{self.port}")
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._client is not None:
            self._client.close()

    def write_snapshot(self, snapshot: TurtleBotStatusSnapshot) -> None:
        for register, value in snapshot.register_values():
            address = to_protocol_address(register, self.zero_based)
            if self.dry_run:
                print(f"DRY-RUN write register={register} address={address} value={value}")
                continue
            assert self._client is not None
            try:
                result = self._client.write_register(address=address, value=int(value), device_id=self.unit_id)
            except TypeError:
                result = self._client.write_register(address=address, value=int(value), slave=self.unit_id)
            if result.isError():
                raise RuntimeError(f"Modbus write failed register={register} address={address}: {result}")


def clamp_percent(value: float) -> int:
    if value != value:  # NaN
        return 0
    return max(0, min(100, int(round(value))))


def run_without_ros(args: argparse.Namespace) -> int:
    snapshot = TurtleBotStatusSnapshot(
        status=args.status,
        nav_state=args.nav_state,
        battery_percent=args.battery_percent,
        current_goal=args.current_goal,
        heartbeat=args.heartbeat_start,
    )
    with ModbusRegisterWriter(args.host, args.port, args.unit_id, args.zero_based_addresses, args.dry_run) as writer:
        writer.write_snapshot(snapshot)
    return 0


def run_with_ros(args: argparse.Namespace) -> int:
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import BatteryState

    class HeartbeatNode(Node):
        def __init__(self):
            super().__init__('turtlebot_modbus_heartbeat')
            self.snapshot = TurtleBotStatusSnapshot(
                status=args.status,
                nav_state=args.nav_state,
                battery_percent=args.battery_percent,
                current_goal=args.current_goal,
                heartbeat=args.heartbeat_start,
            )
            self.writer = ModbusRegisterWriter(
                args.host,
                args.port,
                args.unit_id,
                args.zero_based_addresses,
                args.dry_run,
            )
            self.writer.__enter__()
            self.create_subscription(BatteryState, '/battery_state', self._on_battery, 10)
            self.timer = self.create_timer(args.interval_sec, self._tick)

        def destroy_node(self):
            self.writer.__exit__(None, None, None)
            super().destroy_node()

        def _on_battery(self, msg: BatteryState) -> None:
            if msg.percentage >= 0.0:
                self.snapshot.battery_percent = clamp_percent(msg.percentage * 100.0)

        def _tick(self) -> None:
            self.snapshot.heartbeat = (self.snapshot.heartbeat + 1) % 65536
            self.writer.write_snapshot(self.snapshot)
            self.get_logger().info(
                f"status={self.snapshot.status} nav={self.snapshot.nav_state} "
                f"battery={self.snapshot.battery_percent}% goal={self.snapshot.current_goal} "
                f"heartbeat={self.snapshot.heartbeat}"
            )
            if args.once:
                rclpy.shutdown()

    rclpy.init()
    node = HeartbeatNode()
    try:
        rclpy.spin(node)
    finally:
        if rclpy.ok():
            rclpy.shutdown()
        node.destroy_node()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='192.168.110.109', help='Modbus server host')
    parser.add_argument('--port', type=int, default=50200, help='Modbus server port')
    parser.add_argument('--unit-id', type=int, default=1, help='Modbus unit/device id')
    parser.add_argument('--literal-addresses', dest='zero_based_addresses', action='store_false', help='Use literal 400xx addresses instead of zero-based protocol addresses')
    parser.set_defaults(zero_based_addresses=True)
    parser.add_argument('--dry-run', action='store_true', help='Print writes instead of connecting to Modbus')
    parser.add_argument('--once', action='store_true', help='Write one heartbeat and exit')
    parser.add_argument('--no-ros', action='store_true', help='Do not initialize rclpy; useful for smoke tests')
    parser.add_argument('--interval-sec', type=float, default=1.0, help='Heartbeat interval')
    parser.add_argument('--status', type=int, default=STATUS_IDLE, help='turtlebot_status enum value')
    parser.add_argument('--nav-state', type=int, default=NAV_STATE_UNKNOWN, help='turtlebot_nav_state enum value')
    parser.add_argument('--battery-percent', type=int, default=0, help='fallback battery percent')
    parser.add_argument('--current-goal', type=int, default=CURRENT_GOAL_NONE, help='current goal index')
    parser.add_argument('--heartbeat-start', type=int, default=0, help='initial heartbeat value')
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.no_ros:
        return run_without_ros(args)
    return run_with_ros(args)


if __name__ == '__main__':
    raise SystemExit(main())

"""Manual Modbus command sender for the SmartFarmProject conveyor."""

from __future__ import annotations

import argparse
import sys

from realsense.conveyor_modbus import (
    ConveyorModbusTcpClient,
    command_name,
    parse_conveyor_command,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send one manual command to the conveyor Modbus TCP server."
    )
    parser.add_argument(
        "command",
        help=(
            "stop | run_clockwise | run_counter_clockwise | reset | emergency_stop "
            "(aliases: cw, ccw, estop)"
        ),
    )
    parser.add_argument("--host", default="192.168.110.109", help="Modbus TCP server IP")
    parser.add_argument("--port", type=int, default=50200, help="Modbus TCP server port")
    parser.add_argument("--unit-id", type=int, default=1, help="Modbus slave/unit id")
    parser.add_argument("--speed", type=int, default=0, help="Value for 40022 conveyor_speed_cmd")
    parser.add_argument("--timeout", type=float, default=1.0, help="Connection timeout seconds")
    parser.add_argument(
        "--absolute-addresses",
        action="store_true",
        help="Use literal 40021-style addresses instead of pymodbus zero-based addresses.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and print the command without opening a TCP connection.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        command_value = parse_conveyor_command(args.command)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    client = ConveyorModbusTcpClient(
        host=args.host,
        port=args.port,
        unit_id=args.unit_id,
        timeout=args.timeout,
        zero_based_addresses=not args.absolute_addresses,
        dry_run=args.dry_run,
    )
    ok = client.write_command(command_value, speed_cmd=args.speed)
    client.close()

    mode = "DRY-RUN " if args.dry_run else ""
    print(
        f"{mode}command={command_value}({command_name(command_value)}) "
        f"speed={args.speed} target={args.host}:{args.port} ok={ok}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

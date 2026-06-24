#!/usr/bin/env python3
"""Smoke-test client for the SmartFarmProject Modbus server."""

from __future__ import annotations

import argparse
import asyncio
from typing import Sequence

from register_map import (
    DEFAULT_DEVICE_ID,
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
    REGISTER_CONVEYOR_COMMAND,
    REGISTER_CONVEYOR_SPEED_CMD,
    SHARED_BLOCK_COUNT,
    SHARED_BLOCK_START_ADDRESS,
    protocol_address,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read/write smoke test for SmartFarmProject Modbus server")
    parser.add_argument("--host", default=DEFAULT_SERVER_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_SERVER_PORT)
    parser.add_argument("--device-id", type=int, default=DEFAULT_DEVICE_ID)
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--write-demo", action="store_true", help="Write stop/default speed and read back")
    return parser


async def async_main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from pymodbus.client import AsyncModbusTcpClient  # type: ignore

    client = AsyncModbusTcpClient(args.host, port=args.port, timeout=args.timeout)
    try:
        ok = await client.connect()
        if not ok:
            print(f"CONNECT FAIL {args.host}:{args.port}")
            return 1
        result = await client.read_holding_registers(
            SHARED_BLOCK_START_ADDRESS,
            count=min(SHARED_BLOCK_COUNT, 80),
            device_id=args.device_id,
        )
        if result.isError():
            print(f"READ ERROR {result}")
            return 2
        print(f"READ OK {args.host}:{args.port} count={len(result.registers)} first10={result.registers[:10]}")

        if args.write_demo:
            command_addr = protocol_address(REGISTER_CONVEYOR_COMMAND)
            speed_addr = protocol_address(REGISTER_CONVEYOR_SPEED_CMD)
            wr1 = await client.write_register(command_addr, 0, device_id=args.device_id)
            wr2 = await client.write_register(speed_addr, 0, device_id=args.device_id)
            if wr1.isError() or wr2.isError():
                print(f"WRITE ERROR command={wr1} speed={wr2}")
                return 3
            rr = await client.read_holding_registers(command_addr, count=2, device_id=args.device_id)
            if rr.isError():
                print(f"READBACK ERROR {rr}")
                return 4
            print(f"WRITE DEMO OK 40021/40022={rr.registers[:2]}")
        return 0
    finally:
        close = getattr(client, "close", None)
        if close is not None:
            maybe = close()
            if hasattr(maybe, "__await__"):
                await maybe


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())

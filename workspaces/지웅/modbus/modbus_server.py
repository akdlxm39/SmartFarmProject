#!/usr/bin/env python3
"""SmartFarmProject Modbus TCP shared register server.

Default endpoint is 192.168.110.109:50200. This server only owns the shared
holding-register layer. Device-specific clients (PC vision, Raspberry Pi,
future Dobot/TurtleBot clients) own writes to their assigned registers.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Sequence

from register_map import (
    DEFAULT_DEVICE_ID,
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
    SERVER_HR_COUNT,
    initial_holding_registers,
    markdown_register_table,
)

LOG = logging.getLogger("smartfarm_modbus_server")


def _build_context(device_id: int):
    """Build a pymodbus 3.13 simulator-backed server context.

    The user's earlier pymodbus examples used ``StartAsyncTcpServer`` with
    ``SimDevice`` entries. In pymodbus 3.13 this is the API shape that the
    server expects, so the project server keeps that approach and layers the
    SmartFarm register map on top of the holding-register values.
    """
    from pymodbus.simulator import DataType, SimData, SimDevice  # type: ignore

    values = initial_holding_registers(SERVER_HR_COUNT)
    holding_registers = SimData(
        address=0,
        values=values,
        datatype=DataType.REGISTERS,
    )
    input_registers = SimData(
        address=0,
        values=[0] * SERVER_HR_COUNT,
        datatype=DataType.REGISTERS,
    )
    return [
        SimDevice(
            id=int(device_id),
            simdata=(
                [SimData(0, count=SERVER_HR_COUNT, values=False, datatype=DataType.BITS)],
                [SimData(0, count=SERVER_HR_COUNT, values=False, datatype=DataType.BITS)],
                [holding_registers],
                [input_registers],
            ),
        )
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the SmartFarmProject Modbus TCP server")
    parser.add_argument("--host", default=DEFAULT_SERVER_HOST, help="Bind host/IP, default: 192.168.110.109")
    parser.add_argument("--port", type=int, default=DEFAULT_SERVER_PORT, help="TCP port, default: 50200")
    parser.add_argument("--device-id", type=int, default=DEFAULT_DEVICE_ID, help="Modbus device/unit id")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--print-register-map", action="store_true", help="Print register ownership table before serving")
    return parser


async def async_main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if args.print_register_map:
        print(markdown_register_table())

    context = _build_context(device_id=args.device_id)
    from pymodbus.server import StartAsyncTcpServer  # type: ignore

    LOG.info("starting Modbus TCP server on %s:%s device_id=%s", args.host, args.port, args.device_id)
    await StartAsyncTcpServer(context=context, address=(args.host, int(args.port)))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())

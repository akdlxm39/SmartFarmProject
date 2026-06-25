#!/usr/bin/env python3
"""Slow GPIO level diagnostic for checking conveyor driver input wiring.

This script is for multimeter/LED/logic-probe checks. It bypasses Modbus and
motor control and slowly drives ENABLE, DIR, and STEP so you can verify whether
voltage changes actually reach the motor driver terminals.
"""

from __future__ import annotations

import argparse
import logging
import time
from typing import Sequence

LOG = logging.getLogger("gpio_level_diagnostic")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Slow STEP/DIR/ENABLE GPIO level test")
    parser.add_argument("--gpio-chip", default="gpiochip0")
    parser.add_argument("--dir-pin", type=int, default=17)
    parser.add_argument("--step-pin", type=int, default=27)
    parser.add_argument("--enable-pin", type=int, default=22)
    parser.add_argument("--enable-active-low", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--cycles", type=int, default=20)
    parser.add_argument("--interval-sec", type=float, default=0.5)
    parser.add_argument("--log-level", default="INFO")
    return parser


def enable_value(enabled: bool, active_low: bool) -> int:
    if active_low:
        return 0 if enabled else 1
    return 1 if enabled else 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        import gpiod  # type: ignore
    except ModuleNotFoundError as exc:
        raise SystemExit("Missing gpiod. Install python3-libgpiod and use a --system-site-packages venv.") from exc

    if not hasattr(gpiod.Chip, "get_line"):
        raise SystemExit("This script expects libgpiod v1 API with Chip.get_line().")

    LOG.info(
        "chip=%s dir=%s step=%s enable=%s enable_active_low=%s cycles=%s interval=%.3f",
        args.gpio_chip,
        args.dir_pin,
        args.step_pin,
        args.enable_pin,
        args.enable_active_low,
        args.cycles,
        args.interval_sec,
    )

    chip = gpiod.Chip(args.gpio_chip)
    dir_line = chip.get_line(args.dir_pin)
    step_line = chip.get_line(args.step_pin)
    enable_line = chip.get_line(args.enable_pin)

    dir_line.request(consumer="conveyor_level_dir", type=gpiod.LINE_REQ_DIR_OUT)
    step_line.request(consumer="conveyor_level_step", type=gpiod.LINE_REQ_DIR_OUT)
    enable_line.request(consumer="conveyor_level_enable", type=gpiod.LINE_REQ_DIR_OUT)

    try:
        en_on = enable_value(True, args.enable_active_low)
        en_off = enable_value(False, args.enable_active_low)
        LOG.info("setting ENABLE active value=%s for measurement", en_on)
        enable_line.set_value(en_on)
        time.sleep(args.interval_sec)

        for i in range(max(1, args.cycles)):
            dir_value = i % 2
            step_value = i % 2
            dir_line.set_value(dir_value)
            step_line.set_value(step_value)
            LOG.info(
                "cycle=%s measure at driver terminals: ENABLE=%s DIR=%s STEP=%s",
                i + 1,
                en_on,
                dir_value,
                step_value,
            )
            time.sleep(args.interval_sec)

        LOG.info("setting ENABLE inactive value=%s", en_off)
        enable_line.set_value(en_off)
        step_line.set_value(0)
    finally:
        for line in (dir_line, step_line, enable_line):
            try:
                line.release()
            except Exception:
                LOG.exception("failed to release GPIO line")
        close = getattr(chip, "close", None)
        if close is not None:
            close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

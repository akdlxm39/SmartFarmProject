#!/usr/bin/env python3
"""Direct GPIO pulse diagnostic for the SmartFarm conveyor stepper driver.

This bypasses Modbus and the controller state machine. Use it on the Raspberry Pi
only when the conveyor area is safe. It drives DIR/ENABLE/STEP directly so we can
separate software command issues from wiring/driver/power issues.
"""

from __future__ import annotations

import argparse
import logging
import time
from typing import Sequence

LOG = logging.getLogger("gpio_pulse_diagnostic")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Direct STEP/DIR/ENABLE GPIO pulse test")
    parser.add_argument("--gpio-chip", default="gpiochip0")
    parser.add_argument("--dir-pin", type=int, default=17)
    parser.add_argument("--step-pin", type=int, default=27)
    parser.add_argument("--enable-pin", type=int, default=22)
    parser.add_argument("--direction", choices=["cw", "ccw"], default="cw")
    parser.add_argument(
        "--enable-active-low",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Default True: enable motor with 0 and disable with 1.",
    )
    parser.add_argument("--pulse-delay-sec", type=float, default=0.001, help="High/low delay per half pulse")
    parser.add_argument("--duration-sec", type=float, default=3.0)
    parser.add_argument("--log-level", default="INFO")
    return parser


def set_enable(line, enabled: bool, active_low: bool) -> None:
    if active_low:
        line.set_value(0 if enabled else 1)
    else:
        line.set_value(1 if enabled else 0)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        import gpiod  # type: ignore
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Python gpiod binding is missing. Install with: "
            "sudo apt install -y gpiod python3-libgpiod; "
            "then recreate venv with --system-site-packages."
        ) from exc

    if not hasattr(gpiod.Chip, "get_line"):
        raise SystemExit(
            "Imported gpiod does not expose Chip.get_line; this diagnostic expects "
            "libgpiod v1 Python API from python3-libgpiod."
        )

    LOG.info(
        "opening chip=%s dir=%s step=%s enable=%s direction=%s enable_active_low=%s pulse_delay=%.6f duration=%.2f",
        args.gpio_chip,
        args.dir_pin,
        args.step_pin,
        args.enable_pin,
        args.direction,
        args.enable_active_low,
        args.pulse_delay_sec,
        args.duration_sec,
    )

    chip = gpiod.Chip(args.gpio_chip)
    dir_line = chip.get_line(args.dir_pin)
    step_line = chip.get_line(args.step_pin)
    enable_line = chip.get_line(args.enable_pin)

    dir_line.request(consumer="conveyor_diag_dir", type=gpiod.LINE_REQ_DIR_OUT)
    step_line.request(consumer="conveyor_diag_step", type=gpiod.LINE_REQ_DIR_OUT)
    enable_line.request(consumer="conveyor_diag_enable", type=gpiod.LINE_REQ_DIR_OUT)

    pulse_count = 0
    try:
        dir_value = 0 if args.direction == "cw" else 1
        dir_line.set_value(dir_value)
        set_enable(enable_line, True, args.enable_active_low)
        LOG.info("enabled driver; DIR=%s. Pulsing STEP now.", dir_value)
        deadline = time.monotonic() + max(0.0, args.duration_sec)
        while time.monotonic() < deadline:
            step_line.set_value(1)
            time.sleep(args.pulse_delay_sec)
            step_line.set_value(0)
            time.sleep(args.pulse_delay_sec)
            pulse_count += 1
        LOG.info("pulse test done pulses=%s", pulse_count)
    finally:
        try:
            set_enable(enable_line, False, args.enable_active_low)
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

#!/usr/bin/env python3
"""Actuator-shield diagnostic for conveyor stepper + servo + buttons.

Use this on the Raspberry Pi when the shield wiring is already assembled.
It keeps the test at the shield interface level:

1. Read the two buttons to prove input GPIO and chip selection.
2. Hold a 50 Hz servo signal on GPIO18 long enough to verify servo power/signal.
3. Drive STEP/DIR/ENABLE on GPIO17/27/22 slowly enough to see/hear motion.

If buttons work but both servo and stepper do not move, the likely shared fault is
not Modbus/controller code. Check shield actuator power/enable/jumpers, shield pin
mapping/interface type, and whether the shield expects I2C/PWM-driver commands
instead of raw GPIO pulses.
"""

from __future__ import annotations

import argparse
import logging
import time
from typing import Sequence

LOG = logging.getLogger("shield_actuator_diagnostic")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Conveyor shield button/servo/stepper diagnostic")
    parser.add_argument("--gpio-chip", default="gpiochip0")
    parser.add_argument("--button1-pin", type=int, default=23)
    parser.add_argument("--button2-pin", type=int, default=24)
    parser.add_argument("--servo-pin", type=int, default=18)
    parser.add_argument("--dir-pin", type=int, default=17)
    parser.add_argument("--step-pin", type=int, default=27)
    parser.add_argument("--enable-pin", type=int, default=22)
    parser.add_argument("--enable-active-low", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--mode",
        choices=["buttons", "servo", "stepper", "all"],
        default="all",
        help="Which shield layer to test.",
    )
    parser.add_argument("--button-sec", type=float, default=8.0)
    parser.add_argument("--servo-angle", type=float, default=135.0)
    parser.add_argument("--servo-hold-sec", type=float, default=3.0)
    parser.add_argument("--stepper-sec", type=float, default=4.0)
    parser.add_argument("--step-delay-sec", type=float, default=0.002)
    parser.add_argument("--log-level", default="INFO")
    return parser


def require_gpiod():
    try:
        import gpiod  # type: ignore
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing Python gpiod binding. On Pi: sudo apt install -y gpiod python3-libgpiod; "
            "then recreate venv with python3 -m venv --system-site-packages .venv"
        ) from exc
    if not hasattr(gpiod.Chip, "get_line"):
        raise SystemExit("This script expects libgpiod v1 API with Chip.get_line().")
    return gpiod


def enable_value(enabled: bool, active_low: bool) -> int:
    if active_low:
        return 0 if enabled else 1
    return 1 if enabled else 0


def angle_to_pulse_width_sec(angle: float) -> float:
    """Map existing project angle convention 0..270 deg to 0.5..2.5 ms."""
    bounded = min(270.0, max(0.0, float(angle)))
    return (bounded / 270.0) * (0.0025 - 0.0005) + 0.0005


def release_lines(*lines: object) -> None:
    for line in lines:
        if line is None:
            continue
        try:
            line.release()  # type: ignore[attr-defined]
        except Exception:
            LOG.exception("failed to release GPIO line")


def test_buttons(gpiod, chip, button1_pin: int, button2_pin: int, duration_sec: float) -> None:
    b1 = chip.get_line(button1_pin)
    b2 = chip.get_line(button2_pin)
    b1.request(consumer="shield_diag_button1", type=gpiod.LINE_REQ_DIR_IN, flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP)
    b2.request(consumer="shield_diag_button2", type=gpiod.LINE_REQ_DIR_IN, flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP)
    try:
        LOG.info("BUTTON test %.1fs: press/release both buttons now. active-low: pressed=0", duration_sec)
        deadline = time.monotonic() + max(0.1, duration_sec)
        last = None
        while time.monotonic() < deadline:
            state = (int(b1.get_value()), int(b2.get_value()))
            if state != last:
                LOG.info("buttons raw: button1=%s button2=%s", state[0], state[1])
                last = state
            time.sleep(0.05)
    finally:
        release_lines(b1, b2)


def test_servo(gpiod, chip, servo_pin: int, angle: float, hold_sec: float) -> None:
    servo = chip.get_line(servo_pin)
    servo.request(consumer="shield_diag_servo", type=gpiod.LINE_REQ_DIR_OUT)
    pulse = angle_to_pulse_width_sec(angle)
    period = 0.020
    try:
        LOG.info(
            "SERVO test: pin=%s angle=%.1f pulse_width=%.4fms hold=%.1fs. "
            "Measure signal pin if it does not move.",
            servo_pin,
            angle,
            pulse * 1000,
            hold_sec,
        )
        deadline = time.monotonic() + max(0.1, hold_sec)
        pulses = 0
        while time.monotonic() < deadline:
            servo.set_value(1)
            time.sleep(pulse)
            servo.set_value(0)
            time.sleep(max(0.0, period - pulse))
            pulses += 1
        LOG.info("SERVO test done pulses=%s", pulses)
    finally:
        try:
            servo.set_value(0)
        finally:
            release_lines(servo)


def test_stepper(
    gpiod,
    chip,
    dir_pin: int,
    step_pin: int,
    enable_pin: int,
    active_low: bool,
    duration_sec: float,
    step_delay_sec: float,
) -> None:
    direction = chip.get_line(dir_pin)
    step = chip.get_line(step_pin)
    enable = chip.get_line(enable_pin)
    direction.request(consumer="shield_diag_dir", type=gpiod.LINE_REQ_DIR_OUT)
    step.request(consumer="shield_diag_step", type=gpiod.LINE_REQ_DIR_OUT)
    enable.request(consumer="shield_diag_enable", type=gpiod.LINE_REQ_DIR_OUT)
    pulses = 0
    try:
        LOG.info(
            "STEPPER test: dir=%s step=%s enable=%s enable_active_low=%s duration=%.1fs delay=%.4fs",
            dir_pin,
            step_pin,
            enable_pin,
            active_low,
            duration_sec,
            step_delay_sec,
        )
        direction.set_value(0)
        enable.set_value(enable_value(True, active_low))
        deadline = time.monotonic() + max(0.1, duration_sec)
        while time.monotonic() < deadline:
            step.set_value(1)
            time.sleep(step_delay_sec)
            step.set_value(0)
            time.sleep(step_delay_sec)
            pulses += 1
        LOG.info("STEPPER test done pulses=%s", pulses)
    finally:
        try:
            enable.set_value(enable_value(False, active_low))
            step.set_value(0)
        finally:
            release_lines(direction, step, enable)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    gpiod = require_gpiod()
    chip = gpiod.Chip(args.gpio_chip)
    try:
        LOG.info("opened %s; mode=%s", args.gpio_chip, args.mode)
        if args.mode in {"buttons", "all"}:
            test_buttons(gpiod, chip, args.button1_pin, args.button2_pin, args.button_sec)
        if args.mode in {"servo", "all"}:
            test_servo(gpiod, chip, args.servo_pin, args.servo_angle, args.servo_hold_sec)
        if args.mode in {"stepper", "all"}:
            test_stepper(
                gpiod,
                chip,
                args.dir_pin,
                args.step_pin,
                args.enable_pin,
                args.enable_active_low,
                args.stepper_sec,
                args.step_delay_sec,
            )
    finally:
        close = getattr(chip, "close", None)
        if close is not None:
            close()
    LOG.info("diagnostic finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

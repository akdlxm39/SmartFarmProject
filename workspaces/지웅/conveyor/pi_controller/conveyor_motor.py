"""GPIO motor and button helpers for the Raspberry Pi conveyor controller."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple

from motion_profile import (
    INITIAL_STEP_DELAY_SEC,
    TARGET_STEP_DELAY_SEC,
    next_accel_delay,
    next_decel_delay,
    speed_cmd_to_target_delay,
)

LOG = logging.getLogger(__name__)

DIR_PIN = 17
STEP_PIN = 27
ENABLE_PIN = 22
BUTTON_EMERGENCY_PIN = 23
BUTTON_RESTART_PIN = 24

DIRECTION_CLOCKWISE = "clockwise"
DIRECTION_COUNTER_CLOCKWISE = "counter_clockwise"


@dataclass(frozen=True)
class ButtonEvents:
    emergency_pressed: bool = False
    restart_pressed: bool = False


class ConveyorMotor:
    """Control a step/dir conveyor driver.

    `dry_run=True` avoids importing gpiod and is safe for PC/unit tests.
    """

    def __init__(
        self,
        dry_run: bool = False,
        gpio_chip: str = "gpiochip0",
        dir_pin: int = DIR_PIN,
        step_pin: int = STEP_PIN,
        enable_pin: int = ENABLE_PIN,
    ) -> None:
        self.dry_run = bool(dry_run)
        self.gpio_chip = gpio_chip
        self.dir_pin = int(dir_pin)
        self.step_pin = int(step_pin)
        self.enable_pin = int(enable_pin)
        self._chip = None
        self._dir_line = None
        self._step_line = None
        self._enable_line = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self.running = False
        self.direction: Optional[str] = None
        self.target_delay = TARGET_STEP_DELAY_SEC
        self.current_delay = INITIAL_STEP_DELAY_SEC
        self.action_log = []
        if not self.dry_run:
            self._setup_gpio()

    def _setup_gpio(self) -> None:
        import gpiod  # type: ignore

        self._chip = gpiod.Chip(self.gpio_chip)
        self._dir_line = self._chip.get_line(self.dir_pin)
        self._step_line = self._chip.get_line(self.step_pin)
        self._enable_line = self._chip.get_line(self.enable_pin)
        self._dir_line.request(consumer="conveyor_dir", type=gpiod.LINE_REQ_DIR_OUT)
        self._step_line.request(consumer="conveyor_step", type=gpiod.LINE_REQ_DIR_OUT)
        self._enable_line.request(consumer="conveyor_enable", type=gpiod.LINE_REQ_DIR_OUT)
        self._set_enable(False)

    def _set_line(self, line: object, value: int) -> None:
        if self.dry_run:
            return
        line.set_value(int(value))  # type: ignore[attr-defined]

    def _set_enable(self, enabled: bool) -> None:
        # Existing reference: ENABLE=0 active, ENABLE=1 disabled.
        if self._enable_line is not None:
            self._set_line(self._enable_line, 0 if enabled else 1)

    def _set_direction(self, direction: str) -> None:
        # Existing reference: CW -> DIR=0, CCW -> DIR=1.
        value = 0 if direction == DIRECTION_CLOCKWISE else 1
        if self._dir_line is not None:
            self._set_line(self._dir_line, value)

    def _pulse_step(self) -> None:
        if self._step_line is not None:
            self._set_line(self._step_line, 1)
        time.sleep(self.current_delay)
        if self._step_line is not None:
            self._set_line(self._step_line, 0)
        time.sleep(self.current_delay)

    def _run_loop(self) -> None:
        LOG.info("motor step loop started direction=%s target_delay=%.7f", self.direction, self.target_delay)
        while not self._stop_event.is_set():
            with self._lock:
                self.current_delay = next_accel_delay(self.current_delay, self.target_delay)
            self._pulse_step()
        while self.current_delay < INITIAL_STEP_DELAY_SEC:
            with self._lock:
                self.current_delay = next_decel_delay(self.current_delay, INITIAL_STEP_DELAY_SEC)
            self._pulse_step()
        self._set_enable(False)
        with self._lock:
            self.running = False
        LOG.info("motor step loop stopped")

    def _start(self, direction: str, speed_cmd: int = 0) -> None:
        with self._lock:
            self.target_delay = speed_cmd_to_target_delay(speed_cmd)
            self.direction = direction
            self.action_log.append((direction, int(speed_cmd)))
            self._set_direction(direction)
            self._set_enable(True)
            if self.running:
                return
            self.running = True
            self.current_delay = INITIAL_STEP_DELAY_SEC
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, name="conveyor-step", daemon=True)
            self._thread.start()

    def start_clockwise(self, speed_cmd: int = 0) -> None:
        self._start(DIRECTION_CLOCKWISE, speed_cmd=speed_cmd)

    def start_counter_clockwise(self, speed_cmd: int = 0) -> None:
        self._start(DIRECTION_COUNTER_CLOCKWISE, speed_cmd=speed_cmd)

    def stop(self) -> None:
        with self._lock:
            self.action_log.append(("stop",))
            self._stop_event.set()
            thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        self._set_enable(False)
        with self._lock:
            self.running = False
            self.direction = None

    def emergency_stop(self) -> None:
        with self._lock:
            self.action_log.append(("emergency_stop",))
            self._stop_event.set()
        self._set_enable(False)
        with self._lock:
            self.running = False
            self.direction = None

    def close(self) -> None:
        self.emergency_stop()
        for line in (self._dir_line, self._step_line, self._enable_line):
            if line is not None:
                try:
                    line.release()  # type: ignore[attr-defined]
                except Exception:  # pragma: no cover - best effort cleanup
                    LOG.exception("failed to release GPIO line")
        if self._chip is not None:
            close = getattr(self._chip, "close", None)
            if close is not None:
                close()


class ButtonReader:
    """Read active-low emergency/restart buttons."""

    def __init__(
        self,
        dry_run: bool = False,
        gpio_chip: str = "gpiochip0",
        emergency_pin: int = BUTTON_EMERGENCY_PIN,
        restart_pin: int = BUTTON_RESTART_PIN,
        debounce_sec: float = 0.05,
    ) -> None:
        self.dry_run = bool(dry_run)
        self.gpio_chip = gpio_chip
        self.emergency_pin = int(emergency_pin)
        self.restart_pin = int(restart_pin)
        self.debounce_sec = float(debounce_sec)
        self._chip = None
        self._emergency_line = None
        self._restart_line = None
        self._last_emergency = 1
        self._last_restart = 1
        self._last_event_time = 0.0
        if not self.dry_run:
            self._setup_gpio()

    def _setup_gpio(self) -> None:
        import gpiod  # type: ignore

        self._chip = gpiod.Chip(self.gpio_chip)
        self._emergency_line = self._chip.get_line(self.emergency_pin)
        self._restart_line = self._chip.get_line(self.restart_pin)
        self._emergency_line.request(
            consumer="conveyor_emergency_button",
            type=gpiod.LINE_REQ_DIR_IN,
            flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP,
        )
        self._restart_line.request(
            consumer="conveyor_restart_button",
            type=gpiod.LINE_REQ_DIR_IN,
            flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP,
        )

    def poll(self) -> ButtonEvents:
        if self.dry_run:
            return ButtonEvents()
        now = time.monotonic()
        emergency = int(self._emergency_line.get_value())  # type: ignore[union-attr]
        restart = int(self._restart_line.get_value())  # type: ignore[union-attr]
        emergency_pressed = self._last_emergency == 1 and emergency == 0
        restart_pressed = self._last_restart == 1 and restart == 0
        self._last_emergency = emergency
        self._last_restart = restart
        if emergency_pressed or restart_pressed:
            if now - self._last_event_time < self.debounce_sec:
                return ButtonEvents()
            self._last_event_time = now
        return ButtonEvents(emergency_pressed=emergency_pressed, restart_pressed=restart_pressed)

    def close(self) -> None:
        for line in (self._emergency_line, self._restart_line):
            if line is not None:
                try:
                    line.release()  # type: ignore[attr-defined]
                except Exception:  # pragma: no cover
                    LOG.exception("failed to release button line")
        if self._chip is not None:
            close = getattr(self._chip, "close", None)
            if close is not None:
                close()

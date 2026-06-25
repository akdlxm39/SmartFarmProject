"""Motion profile helpers copied from the validated conveyor reference profile."""

from __future__ import annotations

INITIAL_STEP_DELAY_SEC = 0.0005
TARGET_STEP_DELAY_SEC = 0.0001
RAMP_DELTA_SEC = 0.0000005
MIN_SPEED_CMD = 1
MAX_SPEED_CMD = 100


def clamp_speed_cmd(speed_cmd: int) -> int:
    """Clamp external 0~100-ish speed command to a safe 1~100 range.

    A command of 0 means "use default full-speed profile" for compatibility with
    existing manual tools that send speed=0 for stop/emergency commands.
    """
    try:
        speed = int(speed_cmd)
    except (TypeError, ValueError):
        speed = MAX_SPEED_CMD
    if speed == 0:
        return MAX_SPEED_CMD
    return max(MIN_SPEED_CMD, min(speed, MAX_SPEED_CMD))


def speed_cmd_to_target_delay(speed_cmd: int) -> float:
    """Map speed command to target step delay.

    speed=100 -> TARGET_STEP_DELAY_SEC (fastest reference profile)
    speed=1   -> close to INITIAL_STEP_DELAY_SEC (slow/safe)
    """
    speed = clamp_speed_cmd(speed_cmd)
    span = INITIAL_STEP_DELAY_SEC - TARGET_STEP_DELAY_SEC
    return INITIAL_STEP_DELAY_SEC - span * (speed / MAX_SPEED_CMD)


def next_accel_delay(current_delay: float, target_delay: float) -> float:
    """Move current delay toward a faster target delay by one ramp step."""
    return max(float(target_delay), float(current_delay) - RAMP_DELTA_SEC)


def next_decel_delay(current_delay: float, initial_delay: float = INITIAL_STEP_DELAY_SEC) -> float:
    """Move current delay toward the slow/stop delay by one ramp step."""
    return min(float(initial_delay), float(current_delay) + RAMP_DELTA_SEC)

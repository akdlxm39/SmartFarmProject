import math

from motion_profile import (
    INITIAL_STEP_DELAY_SEC,
    RAMP_DELTA_SEC,
    TARGET_STEP_DELAY_SEC,
    next_accel_delay,
    next_decel_delay,
    speed_cmd_to_target_delay,
)


def test_speed_cmd_100_uses_reference_target_speed():
    assert math.isclose(speed_cmd_to_target_delay(100), TARGET_STEP_DELAY_SEC)


def test_speed_cmd_zero_defaults_to_full_speed_reference_profile():
    assert math.isclose(speed_cmd_to_target_delay(0), TARGET_STEP_DELAY_SEC)


def test_speed_cmd_is_clamped_to_safe_range():
    assert math.isclose(speed_cmd_to_target_delay(1000), TARGET_STEP_DELAY_SEC)
    slow_delay = speed_cmd_to_target_delay(-20)
    assert TARGET_STEP_DELAY_SEC < slow_delay <= INITIAL_STEP_DELAY_SEC


def test_acceleration_reduces_delay_until_target():
    current = INITIAL_STEP_DELAY_SEC
    next_delay = next_accel_delay(current, TARGET_STEP_DELAY_SEC)
    assert math.isclose(next_delay, current - RAMP_DELTA_SEC)
    assert math.isclose(next_accel_delay(TARGET_STEP_DELAY_SEC, TARGET_STEP_DELAY_SEC), TARGET_STEP_DELAY_SEC)


def test_deceleration_increases_delay_until_initial():
    current = TARGET_STEP_DELAY_SEC
    next_delay = next_decel_delay(current, INITIAL_STEP_DELAY_SEC)
    assert math.isclose(next_delay, current + RAMP_DELTA_SEC)
    assert math.isclose(next_decel_delay(INITIAL_STEP_DELAY_SEC, INITIAL_STEP_DELAY_SEC), INITIAL_STEP_DELAY_SEC)

import pytest

from register_map import (
    COMMAND_EMERGENCY_STOP,
    COMMAND_RESET,
    COMMAND_RUN_CLOCKWISE,
    COMMAND_RUN_COUNTER_CLOCKWISE,
    COMMAND_STOP,
    REGISTER_CONVEYOR_COMMAND,
    REGISTER_CONVEYOR_RESERVED_3,
    protocol_address,
    parse_command,
)


def test_protocol_address_maps_40021_to_20_and_40030_to_29():
    assert protocol_address(REGISTER_CONVEYOR_COMMAND) == 20
    assert protocol_address(REGISTER_CONVEYOR_RESERVED_3) == 29


def test_protocol_address_rejects_registers_outside_conveyor_block():
    with pytest.raises(ValueError):
        protocol_address(40020)
    with pytest.raises(ValueError):
        protocol_address(40031)


def test_parse_command_accepts_names_and_values():
    assert parse_command("stop") == COMMAND_STOP
    assert parse_command("run_clockwise") == COMMAND_RUN_CLOCKWISE
    assert parse_command("cw") == COMMAND_RUN_CLOCKWISE
    assert parse_command("run_counter_clockwise") == COMMAND_RUN_COUNTER_CLOCKWISE
    assert parse_command("ccw") == COMMAND_RUN_COUNTER_CLOCKWISE
    assert parse_command("reset") == COMMAND_RESET
    assert parse_command("emergency_stop") == COMMAND_EMERGENCY_STOP
    assert parse_command(4) == COMMAND_EMERGENCY_STOP


def test_parse_command_rejects_invalid_values():
    with pytest.raises(ValueError):
        parse_command("run_fast")
    with pytest.raises(ValueError):
        parse_command(99)

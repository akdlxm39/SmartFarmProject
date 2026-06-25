from register_map import (
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
    DOBOT_STATUS_IDLE,
    REGISTER_BY_NAME,
    REGISTER_CONVEYOR_COMMAND,
    REGISTER_DOBOT_COMMAND,
    REGISTER_DOBOT_STATUS,
    REGISTER_SYSTEM_COMMAND,
    REGISTER_SYSTEM_COMMAND_SEQ,
    REGISTER_SYSTEM_STATE,
    REGISTER_TOMATO_BAD_COUNT_HI,
    REGISTER_TOMATO_GOOD_COUNT_LO,
    REGISTER_TURTLEBOT_COMMAND,
    REGISTER_TURTLEBOT_STATUS,
    REGISTER_TURTLEBOT_DELIVERY_COUNT_HI,
    SERVER_HR_COUNT,
    SYSTEM_COMMAND_HARVEST_START,
    SYSTEM_COMMAND_PAUSE_ALL,
    SYSTEM_COMMAND_RESUME_ALL,
    SYSTEM_STATE_IDLE,
    TURTLEBOT_STATUS_IDLE,
    combine_u32,
    initial_holding_registers,
    parse_system_command,
    protocol_address,
    register_number,
    split_u32,
    system_command_name,
)


def test_default_endpoint():
    assert DEFAULT_SERVER_HOST == "192.168.110.109"
    assert DEFAULT_SERVER_PORT == 50200


def test_protocol_address_conversion():
    assert protocol_address(40021) == 20
    assert protocol_address(40030) == 29
    assert protocol_address(40031) == 30
    assert protocol_address(40051) == 50
    assert protocol_address(40071) == 70
    assert register_number(20) == 40021


def test_extended_blocks_are_mapped():
    assert REGISTER_DOBOT_COMMAND == 40031
    assert REGISTER_DOBOT_STATUS == 40035
    assert REGISTER_TURTLEBOT_COMMAND == 40051
    assert REGISTER_TURTLEBOT_STATUS == 40055
    assert REGISTER_SYSTEM_COMMAND == 40071
    assert REGISTER_SYSTEM_COMMAND_SEQ == 40072
    assert REGISTER_SYSTEM_STATE == 40074
    assert REGISTER_TOMATO_GOOD_COUNT_LO == 40081
    assert REGISTER_TOMATO_BAD_COUNT_HI == 40084
    assert REGISTER_TURTLEBOT_DELIVERY_COUNT_HI == 40061
    assert REGISTER_BY_NAME["dobot_status"] == 40035
    assert REGISTER_BY_NAME["turtlebot_status"] == 40055
    assert REGISTER_BY_NAME["system_command"] == 40071


def test_system_command_parser():
    assert parse_system_command("harvest_start") == SYSTEM_COMMAND_HARVEST_START
    assert parse_system_command("pause-all") == SYSTEM_COMMAND_PAUSE_ALL
    assert parse_system_command("resume_all") == SYSTEM_COMMAND_RESUME_ALL
    assert system_command_name(SYSTEM_COMMAND_PAUSE_ALL) == "pause_all"


def test_u32_helpers():
    lo, hi = split_u32(70000)
    assert (lo, hi) == (4464, 1)
    assert combine_u32(lo, hi) == 70000


def test_initial_holding_registers_cover_shared_blocks():
    values = initial_holding_registers()
    assert values[protocol_address(REGISTER_CONVEYOR_COMMAND)] == 0
    assert values[protocol_address(REGISTER_SYSTEM_COMMAND)] == 0
    assert values[protocol_address(REGISTER_SYSTEM_STATE)] == SYSTEM_STATE_IDLE
    assert values[protocol_address(REGISTER_DOBOT_STATUS)] == DOBOT_STATUS_IDLE
    assert values[protocol_address(REGISTER_TURTLEBOT_STATUS)] == TURTLEBOT_STATUS_IDLE
    assert len(values) == SERVER_HR_COUNT
    assert len(values) >= protocol_address(40100) + 1


def test_register_names_are_unique():
    assert len(REGISTER_BY_NAME) == len(set(REGISTER_BY_NAME))

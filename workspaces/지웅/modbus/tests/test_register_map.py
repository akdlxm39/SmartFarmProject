from register_map import (
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
    REGISTER_BY_NAME,
    REGISTER_CONVEYOR_COMMAND,
    REGISTER_DOBOT_STATUS,
    REGISTER_TURTLEBOT_STATUS,
    initial_holding_registers,
    protocol_address,
    register_number,
)


def test_default_endpoint():
    assert DEFAULT_SERVER_HOST == "192.168.110.109"
    assert DEFAULT_SERVER_PORT == 50200


def test_protocol_address_conversion():
    assert protocol_address(40021) == 20
    assert protocol_address(40030) == 29
    assert register_number(20) == 40021


def test_future_blocks_are_reserved():
    assert REGISTER_DOBOT_STATUS == 40031
    assert REGISTER_TURTLEBOT_STATUS == 40051
    assert REGISTER_BY_NAME["dobot_status"] == 40031
    assert REGISTER_BY_NAME["turtlebot_status"] == 40051


def test_initial_holding_registers_cover_conveyor_command():
    values = initial_holding_registers()
    assert values[protocol_address(REGISTER_CONVEYOR_COMMAND)] == 0
    assert len(values) >= protocol_address(40100) + 1

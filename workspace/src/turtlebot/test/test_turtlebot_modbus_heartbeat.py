from turtlebot.turtlebot_modbus_heartbeat import (
    REG_TURTLEBOT_HEARTBEAT,
    REG_TURTLEBOT_STATUS,
    TurtleBotStatusSnapshot,
    to_protocol_address,
)


def test_zero_based_address_conversion():
    assert to_protocol_address(40051) == 50
    assert to_protocol_address(40055) == 54
    assert to_protocol_address(40063) == 62
    assert to_protocol_address(40055, zero_based=False) == 40055


def test_snapshot_registers_include_status_and_heartbeat():
    snapshot = TurtleBotStatusSnapshot(status=1, heartbeat=7)
    values = dict(snapshot.register_values())
    assert values[REG_TURTLEBOT_STATUS] == 1
    assert values[REG_TURTLEBOT_HEARTBEAT] == 7

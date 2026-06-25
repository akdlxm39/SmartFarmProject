from conveyor_modbus_client_controller import ConveyorController
from register_map import (
    COMMAND_EMERGENCY_STOP,
    COMMAND_RESET,
    COMMAND_RUN_CLOCKWISE,
    COMMAND_RUN_COUNTER_CLOCKWISE,
    COMMAND_STOP,
    ERROR_LOCAL_EMERGENCY_STOP,
    ERROR_NONE,
    STATUS_EMERGENCY_STOPPED,
    STATUS_IDLE,
    STATUS_RUNNING,
)


class FakeMotor:
    def __init__(self):
        self.calls = []
        self.running = False

    def start_clockwise(self, speed_cmd=0):
        self.calls.append(("cw", speed_cmd))
        self.running = True

    def start_counter_clockwise(self, speed_cmd=0):
        self.calls.append(("ccw", speed_cmd))
        self.running = True

    def stop(self):
        self.calls.append(("stop",))
        self.running = False

    def emergency_stop(self):
        self.calls.append(("emergency_stop",))
        self.running = False


def test_run_commands_start_motor_and_status_running():
    motor = FakeMotor()
    controller = ConveyorController(motor=motor)

    state = controller.apply_modbus_command(COMMAND_RUN_CLOCKWISE, speed_cmd=80)
    assert motor.calls == [("cw", 80)]
    assert state.status == STATUS_RUNNING
    assert state.error_code == ERROR_NONE

    state = controller.apply_modbus_command(COMMAND_RUN_COUNTER_CLOCKWISE, speed_cmd=60)
    assert motor.calls[-1] == ("ccw", 60)
    assert state.status == STATUS_RUNNING


def test_repeated_run_command_restarts_motor_if_loop_is_no_longer_running():
    motor = FakeMotor()
    controller = ConveyorController(motor=motor)

    controller.apply_modbus_command(COMMAND_RUN_CLOCKWISE, speed_cmd=80)
    motor.running = False

    state = controller.apply_modbus_command(COMMAND_RUN_CLOCKWISE, speed_cmd=80)

    assert motor.calls == [("cw", 80), ("cw", 80)]
    assert state.status == STATUS_RUNNING
    assert state.error_code == ERROR_NONE


def test_stop_and_reset_stop_motor_and_clear_error_when_not_latched():
    motor = FakeMotor()
    controller = ConveyorController(motor=motor)
    controller.apply_modbus_command(COMMAND_RUN_CLOCKWISE, speed_cmd=100)

    state = controller.apply_modbus_command(COMMAND_STOP, speed_cmd=0)
    assert motor.calls[-1] == ("stop",)
    assert state.status == STATUS_IDLE
    assert state.error_code == ERROR_NONE

    state = controller.apply_modbus_command(COMMAND_RESET, speed_cmd=0)
    assert state.status == STATUS_IDLE
    assert state.error_code == ERROR_NONE


def test_local_emergency_stop_latches_and_blocks_run_commands_without_changing_command_register():
    motor = FakeMotor()
    controller = ConveyorController(motor=motor)

    event = controller.handle_emergency_button()
    assert motor.calls == [("emergency_stop",)]
    assert event.status == STATUS_EMERGENCY_STOPPED
    assert event.error_code == ERROR_LOCAL_EMERGENCY_STOP
    assert event.write_command is None

    state = controller.apply_modbus_command(COMMAND_RUN_CLOCKWISE, speed_cmd=100)
    assert motor.calls == [("emergency_stop",)]
    assert state.status == STATUS_EMERGENCY_STOPPED
    assert state.error_code == ERROR_LOCAL_EMERGENCY_STOP
    assert state.write_command is None


def test_restart_button_clears_latch_but_does_not_start_motor():
    motor = FakeMotor()
    controller = ConveyorController(motor=motor)
    controller.handle_emergency_button()

    state = controller.handle_restart_button()
    assert motor.calls == [("emergency_stop",), ("stop",)]
    assert state.status == STATUS_IDLE
    assert state.error_code == ERROR_NONE
    assert state.write_command is None

    state = controller.apply_modbus_command(COMMAND_RUN_CLOCKWISE, speed_cmd=100)
    assert motor.calls[-1] == ("cw", 100)
    assert state.status == STATUS_RUNNING

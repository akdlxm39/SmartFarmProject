import cv2
import numpy as np

from conveyor_vision_test.conveyor_modbus import (
    COLOR_GREEN,
    COLOR_RED,
    COLOR_UNKNOWN,
    COMMAND_EMERGENCY_STOP,
    COMMAND_RUN_CLOCKWISE,
    COMMAND_RUN_COUNTER_CLOCKWISE,
    COMMAND_STOP,
    EVENT_CUBE_DETECTED,
    EVENT_DELIVERED,
    REGISTER_CONVEYOR_COMMAND,
    REGISTER_CONVEYOR_ERROR_CODE,
    REGISTER_CONVEYOR_STATUS,
    REGISTER_CUBE_DETECTED,
    STATUS_DELIVERED,
    STATUS_EMERGENCY_STOPPED,
    STATUS_ERROR,
    STATUS_IDLE,
    STATUS_RUNNING,
    ConveyorModbusTcpClient,
    ConveyorPhysicalState,
    ConveyorVisionStateMachine,
    build_command_write_plan,
    color_code_from_detections,
    parse_conveyor_command,
    register_to_pymodbus_address,
)
from conveyor_vision_test.topview_color_detector import (
    detect_red_green_objects,
    draw_roi_and_detections,
)


class FakeResult:
    def __init__(self, is_error=False):
        self._is_error = is_error

    def isError(self):
        return self._is_error


class FakePymodbusClient:
    def __init__(self, host, port, timeout):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.connected = False
        self.write_registers_calls = []
        self.write_register_calls = []
        self.read_holding_registers_calls = []
        self.register_values = {
            22: [STATUS_IDLE, 0],
        }

    def connect(self):
        self.connected = True
        return True

    def close(self):
        self.connected = False

    def write_registers(self, address, values, slave=1):
        self.write_registers_calls.append((address, list(values), slave))
        return FakeResult(False)

    def write_register(self, address, value, slave=1):
        self.write_register_calls.append((address, value, slave))
        return FakeResult(False)

    def read_holding_registers(self, address, count=1, slave=1):
        self.read_holding_registers_calls.append((address, count, slave))

        class ReadResult:
            def __init__(self, registers):
                self.registers = registers

            def isError(self):
                return False

        return ReadResult(self.register_values[address][:count])


def test_detects_red_and_green_inside_roi_only():
    image = np.zeros((240, 320, 3), dtype=np.uint8)
    roi_polygon = np.array([[40, 30], [280, 30], [280, 210], [40, 210]], dtype=np.int32)

    cv2.rectangle(image, (70, 70), (120, 130), (0, 0, 255), -1)
    cv2.rectangle(image, (180, 90), (240, 150), (0, 255, 0), -1)
    cv2.rectangle(image, (5, 5), (30, 30), (0, 0, 255), -1)  # outside ROI

    detections = detect_red_green_objects(image, roi_polygon, min_area=100.0)

    colors = [detection["color"] for detection in detections]
    assert colors == ["green", "red"]
    assert len(detections) == 2

    red_detection = next(d for d in detections if d["color"] == "red")
    green_detection = next(d for d in detections if d["color"] == "green")
    assert red_detection["bbox_xyxy"] == (70, 70, 121, 131)
    assert green_detection["bbox_xyxy"] == (180, 90, 241, 151)


def test_draw_returns_annotated_image_with_same_shape():
    image = np.zeros((120, 160, 3), dtype=np.uint8)
    roi_polygon = np.array([[10, 10], [140, 10], [140, 100], [10, 100]], dtype=np.int32)
    detections = [
        {"color": "red", "bbox_xyxy": (20, 20, 50, 60), "area": 900.0},
        {"color": "green", "bbox_xyxy": (70, 30, 110, 80), "area": 1200.0},
    ]

    annotated = draw_roi_and_detections(image, roi_polygon, detections)

    assert annotated.shape == image.shape
    assert np.any(annotated != image)


def test_command_map_and_register_addressing():
    assert parse_conveyor_command("stop") == COMMAND_STOP
    assert parse_conveyor_command("run_clockwise") == COMMAND_RUN_CLOCKWISE
    assert parse_conveyor_command("cw") == COMMAND_RUN_CLOCKWISE
    assert parse_conveyor_command("run_counter_clockwise") == COMMAND_RUN_COUNTER_CLOCKWISE
    assert parse_conveyor_command("ccw") == COMMAND_RUN_COUNTER_CLOCKWISE
    assert parse_conveyor_command("emergency_stop") == COMMAND_EMERGENCY_STOP
    assert register_to_pymodbus_address(40021) == 20
    assert register_to_pymodbus_address(40027) == 26
    assert register_to_pymodbus_address(40030) == 29
    assert register_to_pymodbus_address(40021, zero_based=False) == 40021


def test_color_code_from_detections():
    assert color_code_from_detections([]) == 0
    assert color_code_from_detections([{"color": "red"}]) == COLOR_RED
    assert color_code_from_detections([{"color": "green"}]) == COLOR_GREEN
    assert color_code_from_detections([{"color": "red"}, {"color": "green"}]) == COLOR_UNKNOWN


def test_vision_state_machine_runs_until_stable_disappearance():
    machine = ConveyorVisionStateMachine(
        disappear_stable_frames=2,
        run_command=COMMAND_RUN_COUNTER_CLOCKWISE,
        speed_cmd=77,
    )

    idle = machine.update([])
    assert idle.conveyor_command == COMMAND_STOP
    assert idle.conveyor_status == STATUS_IDLE

    running = machine.update([{"color": "green"}])
    assert running.conveyor_command == COMMAND_RUN_COUNTER_CLOCKWISE
    assert running.conveyor_speed_cmd == 77
    assert running.conveyor_status == STATUS_RUNNING
    assert running.cube_detected == 1
    assert running.cube_color == COLOR_GREEN
    assert running.last_vision_event == EVENT_CUBE_DETECTED

    transient_lost = machine.update([])
    assert transient_lost.conveyor_command == COMMAND_RUN_COUNTER_CLOCKWISE
    assert transient_lost.conveyor_status == STATUS_RUNNING
    assert transient_lost.cube_detected == 0

    delivered = machine.update([])
    assert delivered.conveyor_command == COMMAND_STOP
    assert delivered.conveyor_status == STATUS_DELIVERED
    assert delivered.last_vision_event == EVENT_DELIVERED


def test_modbus_client_reads_pi_owned_status_and_error_registers():
    fake_holder = {}

    def factory(host, port, timeout):
        fake_holder["client"] = FakePymodbusClient(host, port, timeout)
        fake_holder["client"].register_values[22] = [STATUS_RUNNING, 0]
        return fake_holder["client"]

    client = ConveyorModbusTcpClient(
        host="192.168.110.109",
        port=50200,
        unit_id=3,
        client_factory=factory,
    )

    physical = client.read_physical_state()

    fake = fake_holder["client"]
    assert physical == ConveyorPhysicalState(
        conveyor_status=STATUS_RUNNING,
        conveyor_error_code=0,
    )
    assert fake.read_holding_registers_calls == [(22, 2, 3)]


def test_command_write_plan_blocks_all_commands_while_emergency_stopped():
    desired = ConveyorVisionStateMachine().update([{"color": "red"}])

    plan = build_command_write_plan(
        desired,
        ConveyorPhysicalState(
            conveyor_status=STATUS_EMERGENCY_STOPPED,
            conveyor_error_code=6,
        ),
    )

    assert plan.command is None
    assert plan.speed_cmd is None
    assert plan.cube_detected == 1
    assert plan.cube_color == COLOR_RED
    assert plan.last_vision_event == EVENT_CUBE_DETECTED
    assert "emergency" in plan.skip_reason


def test_command_write_plan_allows_stop_but_not_run_when_pi_reports_error():
    machine = ConveyorVisionStateMachine(disappear_stable_frames=1)
    run_desired = machine.update([{"color": "green"}])
    stop_desired = machine.update([])

    error_state = ConveyorPhysicalState(
        conveyor_status=STATUS_ERROR,
        conveyor_error_code=9,
    )

    run_plan = build_command_write_plan(run_desired, error_state)
    stop_plan = build_command_write_plan(stop_desired, error_state)

    assert run_plan.command is None
    assert "error" in run_plan.skip_reason
    assert stop_plan.command == COMMAND_STOP


def test_modbus_client_writes_command_speed_and_vision_only_without_status_overwrite():
    fake_holder = {}

    def factory(host, port, timeout):
        fake_holder["client"] = FakePymodbusClient(host, port, timeout)
        fake_holder["client"].register_values[22] = [STATUS_IDLE, 0]
        return fake_holder["client"]

    client = ConveyorModbusTcpClient(
        host="192.168.110.109",
        port=50200,
        unit_id=3,
        client_factory=factory,
    )
    state = ConveyorVisionStateMachine(speed_cmd=77).update([{"color": "red"}])

    assert client.write_vision_command_state(state)
    fake = fake_holder["client"]
    assert fake.host == "192.168.110.109"
    assert fake.port == 50200
    assert fake.write_register_calls == []
    assert fake.write_registers_calls == [
        (20, [COMMAND_RUN_CLOCKWISE, 77], 3),
        (24, [1, COLOR_RED, EVENT_CUBE_DETECTED], 3),
    ]
    written_addresses = [address for address, _values, _unit in fake.write_registers_calls]
    assert register_to_pymodbus_address(REGISTER_CONVEYOR_STATUS) not in written_addresses
    assert register_to_pymodbus_address(REGISTER_CONVEYOR_ERROR_CODE) not in written_addresses


def test_modbus_client_skips_command_but_updates_vision_registers_in_emergency():
    fake_holder = {}

    def factory(host, port, timeout):
        fake_holder["client"] = FakePymodbusClient(host, port, timeout)
        fake_holder["client"].register_values[22] = [STATUS_EMERGENCY_STOPPED, 6]
        return fake_holder["client"]

    client = ConveyorModbusTcpClient(unit_id=3, client_factory=factory)
    state = ConveyorVisionStateMachine(speed_cmd=77).update([{"color": "green"}])

    assert client.write_vision_command_state(state)
    fake = fake_holder["client"]
    assert fake.write_registers_calls == [
        (24, [1, COLOR_GREEN, EVENT_CUBE_DETECTED], 3),
    ]


def test_modbus_client_manual_command_writes_command_and_speed():
    fake_holder = {}

    def factory(host, port, timeout):
        fake_holder["client"] = FakePymodbusClient(host, port, timeout)
        return fake_holder["client"]

    client = ConveyorModbusTcpClient(client_factory=factory)

    assert client.write_command("emergency_stop", speed_cmd=0)
    fake = fake_holder["client"]
    assert fake.write_register_calls == [(20, COMMAND_EMERGENCY_STOP, 1), (21, 0, 1)]

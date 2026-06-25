#!/usr/bin/env python3
"""Minimal Dobot harvest → camera rotation → conveyor test sequence.

Current MVP flow:
1. Operator selects one harvest index.
2. Move to the selected harvest point with the configured jump-move safety path.
3. Turn suction ON and wait 2 seconds.
4. Move to camera position.
5. Rotate end effector 0 → 120 → -120 degrees, waiting 2 seconds at each angle,
   then return to 0 degrees.
6. Temporarily classify as NORMAL and move to conveyor start.
7. Turn suction OFF and return to home.

The harvest index table is generated from the calibration JSON by sorting harvest
points in x-descending, then y-descending order, as requested by the operator.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from dobot_control_pkg.vision_capture_client import CaptureResult, VisionCaptureClient
except ImportError:  # Allows direct source-tree execution with python harvest_test.py.
    from vision_capture_client import CaptureResult, VisionCaptureClient


MM_PER_METER = 1000.0
DEFAULT_SAFE_Z_MM = 100.0
DEFAULT_WAIT_SEC = 2.0
DEFAULT_VELOCITY_RATIO = 0.5
DEFAULT_ACCELERATION_RATIO = 0.5
DEFAULT_HARVEST_Z_MM = -50.0
CAMERA_CAPTURE_ANGLES_DEG = (0.0, 120.0, -120.0)
DEFAULT_CAPTURE_WIDTH = 1280
DEFAULT_CAPTURE_HEIGHT = 720
DEFAULT_CAPTURE_QUALITY = 90
DEFAULT_CAMERA_TIMEOUT_MS = 800
DEFAULT_TCP_TOPIC = "/dobot_TCP"
DEFAULT_RAW_POSE_TOPIC = "/dobot_pose_raw"


@dataclass(frozen=True)
class Pose4:
    x: float
    y: float
    z: float
    r: float = 0.0

    def as_list(self) -> List[float]:
        return [self.x, self.y, self.z, self.r]

    def with_z(self, z: float) -> "Pose4":
        return Pose4(self.x, self.y, z, self.r)

    def with_xy(self, x: float, y: float) -> "Pose4":
        return Pose4(x, y, self.z, self.r)

    def with_r(self, r: float) -> "Pose4":
        return Pose4(self.x, self.y, self.z, r)


@dataclass(frozen=True)
class HarvestTarget:
    index: int
    source_name: str
    pose: Pose4


def destination_for_quality_status(
    quality_status: str,
    conveyor_pose: Pose4,
    defect_box_pose: Pose4,
) -> Tuple[str, Pose4]:
    normalized = quality_status.strip().lower()
    if normalized == "normal":
        return "conveyor normal place", conveyor_pose
    if normalized == "defect":
        return "defect box place", defect_box_pose
    raise ValueError(f"Unsupported quality_status: {quality_status!r}; expected normal or defect")


def quality_status_from_capture_results(results: List[CaptureResult]) -> str:
    """Temporary rule: three successful captures produce a normal verdict.

    Later this function will consume OpenCV/YOLO inference results. If any result
    already returns defect, route to the defect box immediately.
    """
    expected_count = len(CAMERA_CAPTURE_ANGLES_DEG)
    if len(results) != expected_count:
        raise RuntimeError(f"Expected {expected_count} capture results, got {len(results)}")
    statuses = [result.quality_status.strip().lower() for result in results]
    if any(status == "defect" for status in statuses):
        return "defect"
    if all(result.status == "ok" and status == "normal" for result, status in zip(results, statuses)):
        return "normal"
    raise RuntimeError(f"Unsupported capture quality statuses: {statuses}")


def make_sequence_id(harvest_index: int) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"harvest_{harvest_index}_{timestamp}"


def find_package_root_from_file() -> Optional[Path]:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if parent.name == "dobot_control_pkg" and (parent / "package.xml").exists():
            return parent
    return None


def default_calibration_path() -> Path:
    """Resolve the latest calibration JSON in source/install/common execution cases."""
    env_path = os.environ.get("DOBOT_POSITIONS_JSON") or os.environ.get("DOBOT_POSITIONS_OUTPUT")
    if env_path:
        return Path(env_path).expanduser().resolve()

    # Source-tree execution.
    package_root = find_package_root_from_file()
    if package_root is not None:
        source_config = package_root / "config" / "dobot_positions_latest.json"
        if source_config.exists():
            return source_config

    cwd = Path.cwd().resolve()

    # Normal operator flow: cd .../ros2_ws && ros2 run dobot_control_pkg harvest_test
    source_config = cwd / "src" / "dobot_control_pkg" / "config" / "dobot_positions_latest.json"
    if source_config.exists():
        return source_config

    # Legacy first calibration output location.
    workspace_output = cwd / "dobot_positions_latest.json"
    if workspace_output.exists():
        return workspace_output

    # Installed package share, if setup.py installed config files.
    try:
        from ament_index_python.packages import get_package_share_directory

        share_config = (
            Path(get_package_share_directory("dobot_control_pkg"))
            / "config"
            / "dobot_positions_latest.json"
        )
        if share_config.exists():
            return share_config
    except Exception:
        pass

    return source_config


def meters_xyz_to_pose4(position: Dict[str, Any], r_deg: float = 0.0) -> Pose4:
    return Pose4(
        x=float(position["x"]) * MM_PER_METER,
        y=float(position["y"]) * MM_PER_METER,
        z=float(position["z"]) * MM_PER_METER,
        r=float(r_deg),
    )


def quaternion_yaw_deg(x: float, y: float, z: float, w: float) -> float:
    """Return yaw in degrees from a quaternion, used as a fallback TCP r value."""
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.degrees(math.atan2(siny_cosp, cosy_cosp))


def load_calibration(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Calibration JSON not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    positions = data.get("positions")
    if not isinstance(positions, dict):
        raise ValueError("Calibration JSON missing positions object")
    grid = positions.get("harvest_grid")
    if not isinstance(grid, list) or len(grid) != 9:
        raise ValueError("Calibration JSON must contain positions.harvest_grid with 9 items")
    for key in ("camera", "defect_box", "conveyor_start", "home"):
        if key not in positions:
            raise ValueError(f"Calibration JSON missing positions.{key}")
    return data


def build_harvest_targets(calibration: Dict[str, Any], harvest_z_mm: float = DEFAULT_HARVEST_Z_MM) -> List[HarvestTarget]:
    """Assign operator-facing indices by x descending, then y descending."""
    grid = calibration["positions"]["harvest_grid"]
    sorted_items = sorted(
        grid,
        key=lambda item: (-float(item["x"]), -float(item["y"]), float(item["z"])),
    )
    targets: List[HarvestTarget] = []
    for index, item in enumerate(sorted_items, start=1):
        targets.append(
            HarvestTarget(
                index=index,
                source_name=str(item.get("name", f"harvest_source_{index}")),
                pose=meters_xyz_to_pose4(item, r_deg=0.0).with_z(float(harvest_z_mm)),
            )
        )
    return targets


def pose_from_calibration(calibration: Dict[str, Any], key: str, r_deg: float = 0.0) -> Pose4:
    return meters_xyz_to_pose4(calibration["positions"][key], r_deg=r_deg)


def format_pose(pose: Pose4) -> str:
    return f"x={pose.x:.1f}, y={pose.y:.1f}, z={pose.z:.1f}, r={pose.r:.1f}"


def print_harvest_menu(targets: Iterable[HarvestTarget]) -> None:
    print("\n수확 대상 인덱스표 (정렬: x 내림차순 -> y 내림차순, 단위 mm)")
    print("index | source | x | y | z")
    print("----- | ------ | ---: | ---: | ---:")
    for target in targets:
        print(
            f"{target.index:>5} | {target.source_name:<9} | "
            f"{target.pose.x:>6.1f} | {target.pose.y:>6.1f} | {target.pose.z:>6.1f}"
        )


def choose_harvest_index(targets: List[HarvestTarget], requested: Optional[int]) -> int:
    valid = {target.index for target in targets}
    if requested is not None:
        if requested not in valid:
            raise ValueError(f"Invalid harvest index {requested}; choose 1-9")
        return requested

    while True:
        raw = input("\n수확할 인덱스를 입력하세요 [1-9, q=quit]: ").strip().lower()
        if raw == "q":
            raise KeyboardInterrupt("operator cancelled")
        try:
            selected = int(raw)
        except ValueError:
            print("숫자 1~9 또는 q만 입력하세요.")
            continue
        if selected in valid:
            return selected
        print("범위가 잘못되었습니다. 1~9 중 하나를 입력하세요.")


class DobotHarvestTestNode:
    def __init__(
        self,
        *,
        action_name: str,
        suction_service_name: str,
        velocity_ratio: float,
        acceleration_ratio: float,
        tcp_topic: str,
        raw_pose_topic: str,
        dry_run: bool = False,
    ) -> None:
        self.dry_run = dry_run
        self.velocity_ratio = velocity_ratio
        self.acceleration_ratio = acceleration_ratio
        self.current_pose: Optional[Pose4] = None
        self.latest_raw_pose: Optional[List[float]] = None

        if dry_run:
            self.node = None
            self.PointToPoint = None
            self.GoalStatus = None
            self.SuctionCupControl = None
            self.rclpy = None
            self.action_client = None
            self.suction_client = None
            self.tcp_subscription = None
            self.raw_pose_subscription = None
            return

        import rclpy
        from action_msgs.msg import GoalStatus
        from dobot_msgs.action import PointToPoint
        from dobot_msgs.srv import SuctionCupControl
        from geometry_msgs.msg import PoseStamped
        from rclpy.action import ActionClient
        from rclpy.node import Node
        from std_msgs.msg import Float64MultiArray

        class _Node(Node):
            pass

        self.rclpy = rclpy
        self.GoalStatus = GoalStatus
        self.PointToPoint = PointToPoint
        self.SuctionCupControl = SuctionCupControl
        self.node = _Node("dobot_harvest_test")
        self.action_client = ActionClient(self.node, PointToPoint, action_name)
        self.suction_client = self.node.create_client(SuctionCupControl, suction_service_name)
        self.tcp_subscription = self.node.create_subscription(PoseStamped, tcp_topic, self._tcp_callback, 10)
        self.raw_pose_subscription = self.node.create_subscription(
            Float64MultiArray, raw_pose_topic, self._raw_pose_callback, 10
        )

    def _raw_pose_callback(self, msg: Any) -> None:
        self.latest_raw_pose = list(msg.data)

    def _tcp_callback(self, msg: Any) -> None:
        pose = msg.pose
        orientation = pose.orientation
        r_deg = quaternion_yaw_deg(
            float(orientation.x),
            float(orientation.y),
            float(orientation.z),
            float(orientation.w),
        )
        if self.latest_raw_pose is not None and len(self.latest_raw_pose) >= 4:
            r_deg = float(self.latest_raw_pose[3])
        self.current_pose = Pose4(
            x=float(pose.position.x) * MM_PER_METER,
            y=float(pose.position.y) * MM_PER_METER,
            z=float(pose.position.z) * MM_PER_METER,
            r=r_deg,
        )

    def log(self, message: str) -> None:
        if self.node is not None:
            self.node.get_logger().info(message)
        else:
            print(f"[DRY-RUN] {message}")

    def wait_for_interfaces(self, timeout_sec: float) -> None:
        if self.dry_run:
            self.log("interface wait skipped")
            return

        assert self.action_client is not None
        assert self.suction_client is not None
        self.log("Waiting for /PTP_action action server...")
        if not self.action_client.wait_for_server(timeout_sec=timeout_sec):
            raise RuntimeError("/PTP_action action server not available")

        self.log("Waiting for /dobot_suction_cup_service...")
        if not self.suction_client.wait_for_service(timeout_sec=timeout_sec):
            raise RuntimeError("/dobot_suction_cup_service not available")

    def wait_for_current_pose(self, timeout_sec: float) -> None:
        """Prime current_pose from /dobot_TCP so the first jump move raises z in place."""
        if self.dry_run:
            self.log("current TCP pose wait skipped")
            return

        assert self.rclpy is not None
        assert self.node is not None
        deadline = time.monotonic() + timeout_sec
        while self.current_pose is None and time.monotonic() < deadline:
            self.rclpy.spin_once(self.node, timeout_sec=0.1)

        if self.current_pose is None:
            raise RuntimeError("Current /dobot_TCP pose not received; cannot start safe jump move")
        self.log(f"CURRENT TCP initialized: [{format_pose(self.current_pose)}]")

    def move_ptp(self, pose: Pose4, label: str) -> None:
        self.log(f"MOVE {label}: [{format_pose(pose)}]")
        if self.dry_run:
            self.current_pose = pose
            return

        assert self.rclpy is not None
        assert self.PointToPoint is not None
        assert self.GoalStatus is not None
        assert self.node is not None
        assert self.action_client is not None

        goal = self.PointToPoint.Goal()
        goal.motion_type = 1  # MOTION_TYPE_MOVJ_XYZ
        goal.target_pose = pose.as_list()
        goal.velocity_ratio = self.velocity_ratio
        goal.acceleration_ratio = self.acceleration_ratio

        send_future = self.action_client.send_goal_async(goal)
        self.rclpy.spin_until_future_complete(self.node, send_future)
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            raise RuntimeError(f"PTP goal rejected: {label} -> {pose.as_list()}")

        result_future = goal_handle.get_result_async()
        self.rclpy.spin_until_future_complete(self.node, result_future)
        wrapped_result = result_future.result()
        if wrapped_result is None:
            raise RuntimeError(f"PTP result missing: {label}")
        if wrapped_result.status != self.GoalStatus.STATUS_SUCCEEDED:
            raise RuntimeError(f"PTP goal failed status={wrapped_result.status}: {label}")

        self.current_pose = pose
        self.log(f"DONE {label}: achieved={list(wrapped_result.result.achieved_pose)}")

    def jump_move_to(self, target: Pose4, label: str, safe_z_mm: float) -> None:
        """Move z -> xy -> target z, using the confirmed safe height."""
        if self.current_pose is None:
            # First move: go to target x/y at safe z, then descend/ascend to target z.
            self.move_ptp(Pose4(target.x, target.y, safe_z_mm, target.r), f"{label} safe approach")
        else:
            current_safe = Pose4(self.current_pose.x, self.current_pose.y, safe_z_mm, self.current_pose.r)
            target_safe = Pose4(target.x, target.y, safe_z_mm, target.r)
            if abs(self.current_pose.z - safe_z_mm) > 1e-6:
                self.move_ptp(current_safe, f"{label} raise/lower to safe z")
            self.move_ptp(target_safe, f"{label} xy at safe z")

        if abs(target.z - safe_z_mm) > 1e-6:
            self.move_ptp(target, f"{label} target z")
        else:
            self.current_pose = target

    def set_suction(self, enabled: bool) -> None:
        state = "ON" if enabled else "OFF"
        self.log(f"SUCTION {state}")
        if self.dry_run:
            return

        assert self.rclpy is not None
        assert self.SuctionCupControl is not None
        assert self.node is not None
        assert self.suction_client is not None

        request = self.SuctionCupControl.Request()
        request.enable_suction = bool(enabled)
        future = self.suction_client.call_async(request)
        self.rclpy.spin_until_future_complete(self.node, future)
        response = future.result()
        if response is None:
            raise RuntimeError(f"Suction {state} response missing")
        if not response.success:
            raise RuntimeError(f"Suction {state} failed: {response.message}")
        self.log(f"SUCTION {state} OK: {response.message}")

    def wait(self, seconds: float, label: str) -> None:
        self.log(f"WAIT {seconds:.1f}s: {label}")
        time.sleep(seconds)

    def capture_at_camera_angle(
        self,
        *,
        vision_mode: str,
        vision_client: Optional[VisionCaptureClient],
        sequence_id: str,
        harvest_index: int,
        angle_deg: float,
        wait_sec: float,
        capture_width: int,
        capture_height: int,
        capture_quality: int,
        camera_timeout_ms: int,
    ) -> CaptureResult:
        if vision_mode == "wait":
            self.wait(wait_sec, f"temporary vision wait at {angle_deg:.0f} deg")
            return CaptureResult(
                status="ok",
                quality_status="normal",
                saved_path="",
                angle_deg=float(angle_deg),
                harvest_index=int(harvest_index),
            )
        if vision_mode == "off":
            self.log(f"VISION CAPTURE skipped at {angle_deg:.0f} deg")
            return CaptureResult(
                status="ok",
                quality_status="normal",
                saved_path="",
                angle_deg=float(angle_deg),
                harvest_index=int(harvest_index),
            )
        if vision_mode != "socket":
            raise ValueError(f"Unsupported vision_mode: {vision_mode}")
        if vision_client is None:
            raise RuntimeError("vision_mode=socket requires a VisionCaptureClient")

        self.log(f"VISION CAPTURE request: sequence={sequence_id}, angle={angle_deg:.0f}")
        result = vision_client.capture(
            sequence_id=sequence_id,
            harvest_index=harvest_index,
            angle_deg=angle_deg,
            width=capture_width,
            height=capture_height,
            quality=capture_quality,
            camera_timeout_ms=camera_timeout_ms,
        )
        self.log(
            "VISION CAPTURE OK: "
            f"angle={angle_deg:.0f}, saved={result.saved_path}, quality={result.quality_status}"
        )
        return result

    def run_sequence(
        self,
        *,
        harvest_target: HarvestTarget,
        camera_pose: Pose4,
        conveyor_pose: Pose4,
        defect_box_pose: Pose4,
        home_pose: Pose4,
        safe_z_mm: float,
        wait_sec: float,
        skip_suction: bool,
        vision_mode: str,
        vision_client: Optional[VisionCaptureClient],
        sequence_id: str,
        capture_width: int,
        capture_height: int,
        capture_quality: int,
        camera_timeout_ms: int,
    ) -> None:
        self.log(f"Selected harvest index={harvest_target.index}, source={harvest_target.source_name}")
        self.log(f"Sequence id={sequence_id}")

        self.jump_move_to(harvest_target.pose.with_r(0.0), "harvest", safe_z_mm)
        if not skip_suction:
            self.set_suction(True)
        self.wait(wait_sec, "suction settle after picking")

        self.jump_move_to(camera_pose.with_r(0.0), "camera", safe_z_mm)
        capture_results: List[CaptureResult] = []
        for angle in CAMERA_CAPTURE_ANGLES_DEG:
            self.move_ptp(camera_pose.with_r(angle), f"camera rotation {angle:.0f} deg")
            capture_results.append(
                self.capture_at_camera_angle(
                    vision_mode=vision_mode,
                    vision_client=vision_client,
                    sequence_id=sequence_id,
                    harvest_index=harvest_target.index,
                    angle_deg=angle,
                    wait_sec=wait_sec,
                    capture_width=capture_width,
                    capture_height=capture_height,
                    capture_quality=capture_quality,
                    camera_timeout_ms=camera_timeout_ms,
                )
            )
        self.move_ptp(camera_pose.with_r(0.0), "camera return 0 deg")

        quality_status = quality_status_from_capture_results(capture_results)
        self.log(f"CLASSIFICATION RESULT: {quality_status.upper()} (temporary from capture success)")
        destination_label, destination_pose = destination_for_quality_status(
            quality_status,
            conveyor_pose.with_r(0.0),
            defect_box_pose.with_r(0.0),
        )
        self.jump_move_to(destination_pose, destination_label, safe_z_mm)
        if not skip_suction:
            self.set_suction(False)
        self.jump_move_to(home_pose.with_r(0.0), "return home", safe_z_mm)
        self.log("SEQUENCE COMPLETE")

    def close(self) -> None:
        if self.dry_run:
            return
        assert self.rclpy is not None
        if self.node is not None:
            self.node.destroy_node()
        self.rclpy.shutdown()


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one Dobot harvest-camera-conveyor test sequence from calibrated positions."
    )
    parser.add_argument("--positions", default=str(default_calibration_path()), help="Calibration JSON path")
    parser.add_argument("--harvest-index", type=int, help="Harvest index to run, after x-desc/y-desc reindexing")
    parser.add_argument("--harvest-z-mm", type=float, default=DEFAULT_HARVEST_Z_MM, help="Fixed harvest z in mm")
    parser.add_argument("--safe-z-mm", type=float, default=DEFAULT_SAFE_Z_MM, help="Jump-move safe z in mm")
    parser.add_argument("--wait-sec", type=float, default=DEFAULT_WAIT_SEC, help="Wait seconds for suction/camera pauses")
    parser.add_argument("--velocity-ratio", type=float, default=DEFAULT_VELOCITY_RATIO)
    parser.add_argument("--acceleration-ratio", type=float, default=DEFAULT_ACCELERATION_RATIO)
    parser.add_argument("--action-name", default="/PTP_action")
    parser.add_argument("--suction-service", default="/dobot_suction_cup_service")
    parser.add_argument("--tcp-topic", default=DEFAULT_TCP_TOPIC, help="Current TCP PoseStamped topic for first safe raise")
    parser.add_argument("--raw-topic", default=DEFAULT_RAW_POSE_TOPIC, help="Optional raw pose topic for current r angle")
    parser.add_argument("--skip-suction", action="store_true", help="Move only; do not call suction service")
    parser.add_argument(
        "--vision-mode",
        choices=["wait", "socket", "off"],
        default="wait",
        help="wait=legacy timed wait, socket=request JPG captures, off=skip capture",
    )
    parser.add_argument("--vision-host", default="127.0.0.1", help="Local vision capture daemon host")
    parser.add_argument("--vision-port", type=int, default=5012, help="Local vision capture daemon port")
    parser.add_argument("--vision-timeout-sec", type=float, default=10.0, help="Vision capture request timeout")
    parser.add_argument("--capture-width", type=int, default=DEFAULT_CAPTURE_WIDTH)
    parser.add_argument("--capture-height", type=int, default=DEFAULT_CAPTURE_HEIGHT)
    parser.add_argument("--capture-quality", type=int, default=DEFAULT_CAPTURE_QUALITY)
    parser.add_argument("--camera-timeout-ms", type=int, default=DEFAULT_CAMERA_TIMEOUT_MS)
    parser.add_argument("--dry-run", action="store_true", help="Print sequence without connecting to ROS interfaces")
    parser.add_argument("--yes", action="store_true", help="Do not ask for final confirmation before motion")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    calibration_path = Path(args.positions).expanduser().resolve()

    try:
        calibration = load_calibration(calibration_path)
        targets = build_harvest_targets(calibration, harvest_z_mm=args.harvest_z_mm)
        camera_pose = pose_from_calibration(calibration, "camera", r_deg=0.0)
        conveyor_pose = pose_from_calibration(calibration, "conveyor_start", r_deg=0.0)
        defect_box_pose = pose_from_calibration(calibration, "defect_box", r_deg=0.0)
        home_pose = pose_from_calibration(calibration, "home", r_deg=0.0)

        print(f"Calibration JSON: {calibration_path}")
        print_harvest_menu(targets)
        selected_index = choose_harvest_index(targets, args.harvest_index)
        harvest_target = next(target for target in targets if target.index == selected_index)

        print("\n실행할 시퀀스")
        print(f"1. harvest index {harvest_target.index}: {format_pose(harvest_target.pose.with_r(0.0))}")
        print("2. suction ON -> 2초 대기")
        print(f"3. camera: {format_pose(camera_pose.with_r(0.0))}")
        print("4. camera rotation: 0도 대기 -> 120도 대기 -> -120도 대기 -> 0도 복귀")
        print(f"5. vision mode: {args.vision_mode}")
        print("6. result=NORMAL 임시 판정: 3장 캡처 성공 시")
        print(f"7. normal -> conveyor: {format_pose(conveyor_pose.with_r(0.0))} -> suction OFF")
        print(f"8. defect -> defect box: {format_pose(defect_box_pose.with_r(0.0))} -> suction OFF")
        print(f"9. home: {format_pose(home_pose.with_r(0.0))}")
        print(f"10. jump move safe z: {args.safe_z_mm:.1f} mm")

        if not args.yes:
            confirmation = input("\n실제 Dobot 동작을 시작할까요? [s=start, q=quit]: ").strip().lower()
            if confirmation != "s":
                print("사용자 취소. 동작하지 않았습니다.")
                return 130

        if not args.dry_run:
            try:
                import rclpy
            except ImportError as exc:
                print("ERROR: rclpy를 import할 수 없습니다. ROS 2 환경을 source 했는지 확인하세요.", file=sys.stderr)
                print(
                    "예: source /opt/ros/humble/setup.bash && "
                    "source /home/ssafy/ros2/magician_ros2_control_system_ws/install/setup.bash && "
                    "source install/setup.bash",
                    file=sys.stderr,
                )
                print(str(exc), file=sys.stderr)
                return 2
            rclpy.init(args=None)

        controller = DobotHarvestTestNode(
            action_name=args.action_name,
            suction_service_name=args.suction_service,
            velocity_ratio=args.velocity_ratio,
            acceleration_ratio=args.acceleration_ratio,
            tcp_topic=args.tcp_topic,
            raw_pose_topic=args.raw_topic,
            dry_run=args.dry_run,
        )
        vision_client = None
        if args.vision_mode == "socket":
            vision_client = VisionCaptureClient(
                host=args.vision_host,
                port=args.vision_port,
                timeout_sec=args.vision_timeout_sec,
            )
        sequence_id = make_sequence_id(harvest_target.index)
        try:
            controller.wait_for_interfaces(timeout_sec=10.0)
            controller.wait_for_current_pose(timeout_sec=5.0)
            controller.run_sequence(
                harvest_target=harvest_target,
                camera_pose=camera_pose,
                conveyor_pose=conveyor_pose,
                defect_box_pose=defect_box_pose,
                home_pose=home_pose,
                safe_z_mm=args.safe_z_mm,
                wait_sec=args.wait_sec,
                skip_suction=args.skip_suction,
                vision_mode=args.vision_mode,
                vision_client=vision_client,
                sequence_id=sequence_id,
                capture_width=args.capture_width,
                capture_height=args.capture_height,
                capture_quality=args.capture_quality,
                camera_timeout_ms=args.camera_timeout_ms,
            )
        finally:
            controller.close()
        return 0
    except KeyboardInterrupt:
        print("\n사용자 중단.")
        return 130
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

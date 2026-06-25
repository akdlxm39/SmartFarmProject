#!/usr/bin/env python3
"""Interactive Dobot TCP-position calibration helper.

Usage after sourcing ROS 2 + the workspace:

    ros2 run dobot_control_pkg calibrate_positions

The operator manually moves Dobot to each requested point, types `s`, and the
node stores the latest `/dobot_TCP` pose.  The saved JSON can be used later to
update the project coordinate table and control script constants.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import threading
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


CAPTURE_STEPS = [
    (
        "harvest_lower_left",
        "수확 영역 좌하단 위치",
        "3x3 수확 격자의 좌하단 작물 중심 위치로 Dobot TCP를 맞춘 뒤 s를 입력하세요.",
    ),
    (
        "harvest_upper_right",
        "수확 영역 우상단 위치",
        "3x3 수확 격자의 우상단 작물 중심 위치로 Dobot TCP를 맞춘 뒤 s를 입력하세요.",
    ),
    (
        "camera",
        "촬영 위치",
        "1번 카메라 앞 3방향 촬영 위치로 Dobot TCP를 맞춘 뒤 s를 입력하세요.",
    ),
    (
        "defect_box",
        "불량품 상자 위치",
        "불량품 상자 위 드롭 위치로 Dobot TCP를 맞춘 뒤 s를 입력하세요.",
    ),
    (
        "conveyor_start",
        "컨베이어 시작점 위치",
        "정상 작물을 내려놓을 컨베이어 시작점 위치로 Dobot TCP를 맞춘 뒤 s를 입력하세요.",
    ),
]


DEFAULT_HOME_POSITION_M = {"x": 0.15, "y": 0.0, "z": 0.1}


@dataclass
class LatestPose:
    data: Dict[str, Any]
    received_monotonic: float


class PoseCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: Optional[LatestPose] = None

    def update(self, data: Dict[str, Any]) -> None:
        with self._lock:
            self._latest = LatestPose(data=data, received_monotonic=time.monotonic())

    def snapshot(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self._latest is None:
                return None
            data = deepcopy(self._latest.data)
            data["age_sec"] = round(time.monotonic() - self._latest.received_monotonic, 3)
            return data


class DobotTcpCaptureNode:  # Wrapper to keep rclpy imports local to runtime.
    def __init__(self, node_name: str, tcp_topic: str, raw_topic: str = "/dobot_pose_raw") -> None:
        import rclpy
        from geometry_msgs.msg import PoseStamped
        from rclpy.node import Node
        from std_msgs.msg import Float64MultiArray

        class _Node(Node):
            def __init__(self, cache: PoseCache) -> None:
                super().__init__(node_name)
                self.cache = cache
                self.latest_raw: Optional[List[float]] = None
                self.create_subscription(PoseStamped, tcp_topic, self._tcp_callback, 10)
                self.create_subscription(Float64MultiArray, raw_topic, self._raw_callback, 10)
                self.get_logger().info(f"Listening TCP pose topic: {tcp_topic}")
                self.get_logger().info(f"Listening raw pose topic: {raw_topic} (optional reference)")

            def _raw_callback(self, msg: Any) -> None:
                self.latest_raw = list(msg.data)

            def _tcp_callback(self, msg: Any) -> None:
                stamp = msg.header.stamp
                pose = msg.pose
                data = {
                    "topic": tcp_topic,
                    "frame_id": msg.header.frame_id,
                    "stamp": {"sec": int(stamp.sec), "nanosec": int(stamp.nanosec)},
                    "position": {
                        "x": float(pose.position.x),
                        "y": float(pose.position.y),
                        "z": float(pose.position.z),
                    },
                    "orientation": {
                        "x": float(pose.orientation.x),
                        "y": float(pose.orientation.y),
                        "z": float(pose.orientation.z),
                        "w": float(pose.orientation.w),
                    },
                    "raw_pose_reference": self.latest_raw,
                }
                self.cache.update(data)

        self.rclpy = rclpy
        self.cache = PoseCache()
        self.node = _Node(self.cache)
        self._spin_thread = threading.Thread(target=rclpy.spin, args=(self.node,), daemon=True)

    def start(self) -> None:
        self._spin_thread.start()

    def snapshot(self) -> Optional[Dict[str, Any]]:
        return self.cache.snapshot()

    def close(self) -> None:
        self.node.destroy_node()
        self.rclpy.shutdown()
        self._spin_thread.join(timeout=1.0)


def default_output_path() -> Path:
    env_path = os.environ.get("DOBOT_POSITIONS_OUTPUT")
    if env_path:
        return Path(env_path).expanduser().resolve()

    # Source-tree execution: .../src/dobot_control_pkg/dobot_control_pkg/calibrate_positions.py
    here = Path(__file__).resolve()
    for parent in here.parents:
        if parent.name == "dobot_control_pkg" and (parent / "package.xml").exists():
            return parent / "config" / "dobot_positions_latest.json"

    # Installed `ros2 run` execution: __file__ points into install/, so recover the
    # workspace source package from the operator's cwd when launched in ros2_ws.
    cwd = Path.cwd().resolve()
    source_pkg = cwd / "src" / "dobot_control_pkg"
    if (source_pkg / "package.xml").exists():
        return source_pkg / "config" / "dobot_positions_latest.json"

    return cwd / "dobot_positions_latest.json"


def as_xyz(pose_record: Dict[str, Any]) -> Dict[str, float]:
    pos = pose_record["position"]
    return {"x": float(pos["x"]), "y": float(pos["y"]), "z": float(pos["z"])}


def interpolate(a: float, b: float, idx: int, count: int = 3) -> float:
    if count <= 1:
        return a
    return a + (b - a) * (idx / (count - 1))


def generate_harvest_grid(
    lower_left_record: Dict[str, Any],
    upper_right_record: Dict[str, Any],
    z_mode: str,
) -> List[Dict[str, Any]]:
    """Generate 3x3 harvest positions from lower-left and upper-right corners.

    Index order is row-major from lower y to upper y, and left x to right x:
    1 2 3 are the lower row, 7 8 9 are the upper row.
    """
    ll = as_xyz(lower_left_record)
    ur = as_xyz(upper_right_record)
    grid: List[Dict[str, Any]] = []
    for row in range(3):
        for col in range(3):
            idx = row * 3 + col + 1
            x = interpolate(ll["x"], ur["x"], col)
            y = interpolate(ll["y"], ur["y"], row)
            if z_mode == "lower_left":
                z = ll["z"]
            elif z_mode == "upper_right":
                z = ur["z"]
            elif z_mode == "diagonal":
                # With only two measured corners we cannot fit a plane; this is a
                # simple diagonal interpolation fallback if the bed is sloped.
                z = interpolate(ll["z"], ur["z"], row + col, count=5)
            else:  # average, default
                z = (ll["z"] + ur["z"]) / 2.0
            grid.append(
                {
                    "index": idx,
                    "name": f"harvest_{idx}",
                    "x": round(x, 4),
                    "y": round(y, 4),
                    "z": round(z, 4),
                    "row": row,
                    "col": col,
                }
            )
    return grid


def wait_for_first_pose(capture_node: DobotTcpCaptureNode, timeout_sec: float) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if capture_node.snapshot() is not None:
            return True
        time.sleep(0.1)
    return False


def prompt_capture(
    capture_node: DobotTcpCaptureNode,
    key: str,
    title: str,
    instruction: str,
    max_pose_age_sec: float,
) -> Dict[str, Any]:
    print("\n" + "=" * 72)
    print(f"[{key}] {title}")
    print(instruction)
    print("- Dobot을 손으로 원하는 위치까지 움직인 뒤 터미널에 s를 입력하세요.")
    print("- q 입력 시 저장 없이 중단합니다.")

    while True:
        user_input = input("입력 [s=save, q=quit]: ").strip().lower()
        if user_input == "q":
            raise KeyboardInterrupt("operator cancelled")
        if user_input != "s":
            print("s 또는 q만 입력하세요.")
            continue

        snapshot = capture_node.snapshot()
        if snapshot is None:
            print("아직 /dobot_TCP pose를 받은 적이 없습니다. 토픽 연결을 확인하고 다시 s를 입력하세요.")
            continue

        age_sec = float(snapshot.get("age_sec", math.inf))
        if age_sec > max_pose_age_sec:
            print(f"경고: 마지막 pose가 {age_sec:.3f}초 전 값입니다. 최신 토픽 수신을 기다린 뒤 다시 시도하세요.")
            continue

        snapshot["captured_key"] = key
        snapshot["captured_label"] = title
        snapshot["captured_at"] = datetime.now().isoformat(timespec="seconds")
        xyz = as_xyz(snapshot)
        print(f"저장됨: x={xyz['x']:.4f}, y={xyz['y']:.4f}, z={xyz['z']:.4f}, age={age_sec:.3f}s")
        return snapshot


def write_markdown_summary(json_path: Path, result: Dict[str, Any]) -> Path:
    md_path = json_path.with_suffix(".md")
    positions = result["positions"]
    lines = [
        "# Dobot 위치 보정 결과",
        "",
        f"생성 시각: `{result['created_at']}`",
        f"원본 JSON: `{json_path}`",
        "",
        "## 수확 위치 3x3",
        "| index | x | y | z |",
        "|---:|---:|---:|---:|",
    ]
    for item in positions["harvest_grid"]:
        lines.append(f"| {item['index']} | {item['x']} | {item['y']} | {item['z']} |")

    lines.extend(
        [
            "",
            "## 주요 위치",
            "| name | x | y | z |",
            "|---|---:|---:|---:|",
        ]
    )
    for key in ["camera", "defect_box", "conveyor_start", "home"]:
        p = positions[key]
        lines.append(f"| {key} | {p['x']} | {p['y']} | {p['z']} |")

    lines.extend(
        [
            "",
            "## 메모",
            "- 수확 위치는 좌하단/우상단 TCP pose를 기준으로 3x3 분할 생성했다.",
            f"- z 생성 방식: `{result['grid_z_mode']}`",
            "- 홈 위치는 고정 기본값 `(150, 0, 100)mm`를 저장한다.",
            "- JSON의 `raw_captures`에는 원본 `/dobot_TCP` pose와 optional `/dobot_pose_raw` 참조값이 들어 있다.",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path


def build_result(
    captures: Dict[str, Dict[str, Any]],
    tcp_topic: str,
    raw_topic: str,
    z_mode: str,
) -> Dict[str, Any]:
    harvest_grid = generate_harvest_grid(
        captures["harvest_lower_left"],
        captures["harvest_upper_right"],
        z_mode=z_mode,
    )
    return {
        "schema_version": 1,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source": {
            "ros_package": "magician_ros2",
            "tcp_topic": tcp_topic,
            "raw_topic_optional": raw_topic,
            "capture_method": "manual_move_then_input_s",
        },
        "grid_z_mode": z_mode,
        "capture_order": [step[0] for step in CAPTURE_STEPS],
        "raw_captures": captures,
        "positions": {
            "harvest_grid": harvest_grid,
            "camera": as_xyz(captures["camera"]),
            "defect_box": as_xyz(captures["defect_box"]),
            "conveyor_start": as_xyz(captures["conveyor_start"]),
            "home": dict(DEFAULT_HOME_POSITION_M),
        },
        "implementation_notes": [
            "jump move safe z defaults to 100 mm",
            "home position is fixed at x=150 mm, y=0 mm, z=100 mm and harvest_test returns home after each cycle",
            "vision capture/result waits are temporarily replaced by 2-second waits",
            "after moving Dobot hardware, recalibrate and replace old position constants with this file",
        ],
    }


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manually capture Dobot TCP positions from /dobot_TCP and save calibrated coordinates."
    )
    parser.add_argument("--tcp-topic", default="/dobot_TCP", help="PoseStamped TCP pose topic")
    parser.add_argument("--raw-topic", default="/dobot_pose_raw", help="Optional Float64MultiArray raw pose topic")
    parser.add_argument(
        "--output",
        default=str(default_output_path()),
        help="Output JSON path. Default: package config/dobot_positions_latest.json",
    )
    parser.add_argument(
        "--grid-z-mode",
        choices=["average", "lower_left", "upper_right", "diagonal"],
        default="average",
        help="How to generate z values for the 3x3 harvest grid from two corner captures.",
    )
    parser.add_argument("--initial-timeout", type=float, default=10.0, help="Seconds to wait for first TCP pose")
    parser.add_argument("--max-pose-age", type=float, default=1.0, help="Reject snapshots older than this many seconds")
    parser.add_argument("--no-md", action="store_true", help="Do not write a markdown summary next to the JSON")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    try:
        import rclpy
    except ImportError as exc:
        print("ERROR: rclpy를 import할 수 없습니다. ROS 2 환경을 source 했는지 확인하세요.", file=sys.stderr)
        print("예: source /opt/ros/humble/setup.bash && source install/setup.bash", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 2

    rclpy.init(args=None)
    capture_node = DobotTcpCaptureNode(
        node_name="dobot_position_calibrator",
        tcp_topic=args.tcp_topic,
        raw_topic=args.raw_topic,
    )
    capture_node.start()

    output_path = Path(args.output).expanduser().resolve()
    captures: Dict[str, Dict[str, Any]] = {}

    try:
        print("/dobot_TCP 첫 pose 수신 대기 중...")
        if not wait_for_first_pose(capture_node, args.initial_timeout):
            print(
                f"ERROR: {args.initial_timeout}초 동안 {args.tcp_topic} pose를 받지 못했습니다.",
                file=sys.stderr,
            )
            print("magician_ros2 bringup, homing, /dobot_TCP 토픽을 확인하세요.", file=sys.stderr)
            return 1

        for key, title, instruction in CAPTURE_STEPS:
            captures[key] = prompt_capture(
                capture_node,
                key=key,
                title=title,
                instruction=instruction,
                max_pose_age_sec=args.max_pose_age,
            )

        result = build_result(
            captures=captures,
            tcp_topic=args.tcp_topic,
            raw_topic=args.raw_topic,
            z_mode=args.grid_z_mode,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("\n저장 완료:")
        print(f"- JSON: {output_path}")
        if not args.no_md:
            md_path = write_markdown_summary(output_path, result)
            print(f"- Markdown: {md_path}")
        return 0
    except KeyboardInterrupt:
        print("\n사용자 중단. 파일은 저장하지 않았습니다.")
        return 130
    finally:
        capture_node.close()


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Capture all 9 Dobot harvest positions from /dobot_TCP.

This replaces the earlier two-corner interpolation method.  The operator moves
Dobot to every harvest target and presses `s`; the node snapshots the latest
/dobot_TCP pose, keeps the measured x/y, and writes harvest z as a fixed
operator-configured value (default: -50 mm).

Default behavior merges the new 9 harvest positions into the existing
config/dobot_positions_latest.json while preserving camera/defect/conveyor
positions.  A timestamped backup is created before overwriting the file.
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


DEFAULT_HARVEST_Z_MM = -50.0
MM_PER_METER = 1000.0


HARVEST_CAPTURE_STEPS = [
    (
        index,
        f"harvest_{index}",
        f"수확 위치 {index}",
        "인덱스 기준은 x 내림차순 -> y 내림차순입니다. "
        f"해당 순서의 {index}번 작물 중심으로 TCP를 맞춘 뒤 s를 입력하세요.",
    )
    for index in range(1, 10)
]


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


class DobotTcpCaptureNode:
    def __init__(self, node_name: str, tcp_topic: str, raw_topic: str) -> None:
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
                self.cache.update(
                    {
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
                )

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


def default_positions_path() -> Path:
    env_path = os.environ.get("DOBOT_POSITIONS_JSON") or os.environ.get("DOBOT_POSITIONS_OUTPUT")
    if env_path:
        return Path(env_path).expanduser().resolve()

    here = Path(__file__).resolve()
    for parent in here.parents:
        if parent.name == "dobot_control_pkg" and (parent / "package.xml").exists():
            return parent / "config" / "dobot_positions_latest.json"

    cwd = Path.cwd().resolve()
    source_pkg = cwd / "src" / "dobot_control_pkg"
    if (source_pkg / "package.xml").exists():
        return source_pkg / "config" / "dobot_positions_latest.json"

    return cwd / "dobot_positions_latest.json"


def as_xyz(record: Dict[str, Any]) -> Dict[str, float]:
    pos = record["position"]
    return {"x": float(pos["x"]), "y": float(pos["y"]), "z": float(pos["z"])}


def wait_for_first_pose(capture_node: DobotTcpCaptureNode, timeout_sec: float) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if capture_node.snapshot() is not None:
            return True
        time.sleep(0.1)
    return False


def prompt_capture(
    capture_node: DobotTcpCaptureNode,
    *,
    key: str,
    label: str,
    instruction: str,
    max_pose_age_sec: float,
) -> Dict[str, Any]:
    print("\n" + "=" * 72)
    print(f"[{key}] {label}")
    print(instruction)
    print("- Dobot을 직접 원하는 위치까지 움직인 뒤 터미널에 s를 입력하세요.")
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
            print(f"경고: 마지막 pose가 {age_sec:.3f}초 전 값입니다. 최신 토픽 수신 후 다시 시도하세요.")
            continue

        snapshot["captured_key"] = key
        snapshot["captured_label"] = label
        snapshot["captured_at"] = datetime.now().isoformat(timespec="seconds")
        xyz = as_xyz(snapshot)
        print(f"저장됨(raw): x={xyz['x']:.4f}, y={xyz['y']:.4f}, z={xyz['z']:.4f}, age={age_sec:.3f}s")
        return snapshot


def capture_to_harvest_item(index: int, key: str, capture: Dict[str, Any], harvest_z_mm: float) -> Dict[str, Any]:
    xyz = as_xyz(capture)
    return {
        "index": index,
        "name": key,
        "x": round(xyz["x"], 4),
        "y": round(xyz["y"], 4),
        "z": round(harvest_z_mm / MM_PER_METER, 4),
        "z_source": "fixed_operator_setting",
        "fixed_z_mm": float(harvest_z_mm),
        "measured_z": round(xyz["z"], 4),
    }


def load_base_positions(path: Path) -> Dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "schema_version": 1,
        "positions": {},
        "raw_captures": {},
        "implementation_notes": [],
    }


def backup_existing(path: Path) -> Optional[Path]:
    if not path.exists():
        return None
    backup = path.with_name(f"{path.stem}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{path.suffix}")
    backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    md_path = path.with_suffix(".md")
    if md_path.exists():
        md_backup = md_path.with_name(f"{md_path.stem}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{md_path.suffix}")
        md_backup.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")
    return backup


def build_result(
    *,
    base: Dict[str, Any],
    captures: Dict[str, Dict[str, Any]],
    harvest_grid: List[Dict[str, Any]],
    tcp_topic: str,
    raw_topic: str,
    harvest_z_mm: float,
) -> Dict[str, Any]:
    result = deepcopy(base)
    positions = result.setdefault("positions", {})
    positions["harvest_grid"] = harvest_grid

    raw_captures = result.setdefault("raw_captures", {})
    raw_captures["harvest_grid_full"] = captures

    result["schema_version"] = max(int(result.get("schema_version", 1)), 2)
    result["updated_at"] = datetime.now().isoformat(timespec="seconds")
    result["last_harvest_calibration"] = {
        "method": "manual_capture_all_9_harvest_positions",
        "capture_order": [step[1] for step in HARVEST_CAPTURE_STEPS],
        "index_rule": "x_desc_then_y_desc",
        "tcp_topic": tcp_topic,
        "raw_topic_optional": raw_topic,
        "harvest_z_mm": float(harvest_z_mm),
    }
    notes = result.setdefault("implementation_notes", [])
    note = "harvest positions are manually captured for all 9 points; z is fixed to -50 mm unless changed by CLI"
    if note not in notes:
        notes.append(note)
    return result


def write_markdown_summary(path: Path, result: Dict[str, Any]) -> Path:
    md_path = path.with_suffix(".md")
    calibration = result.get("last_harvest_calibration", {})
    grid = result["positions"]["harvest_grid"]
    lines = [
        "# Dobot 수확 위치 9점 보정 결과",
        "",
        f"생성/갱신 시각: `{result.get('updated_at', result.get('created_at', ''))}`",
        f"원본 JSON: `{path}`",
        f"인덱스 기준: `{calibration.get('index_rule', 'x_desc_then_y_desc')}`",
        f"고정 수확 z: `{calibration.get('harvest_z_mm', DEFAULT_HARVEST_Z_MM)} mm`",
        "",
        "## 수확 위치 9점",
        "| index | name | x(m) | y(m) | z(m) | measured_z(m) | x(mm) | y(mm) | z(mm) |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in grid:
        lines.append(
            f"| {item['index']} | {item['name']} | {item['x']:.4f} | {item['y']:.4f} | {item['z']:.4f} | "
            f"{item.get('measured_z', 0.0):.4f} | {item['x'] * 1000:.1f} | {item['y'] * 1000:.1f} | {item['z'] * 1000:.1f} |"
        )
    lines.extend(
        [
            "",
            "## 메모",
            "- 기존 좌하/우상 2점 분할 방식 대신 9개 수확 위치를 모두 직접 캡처한다.",
            "- x/y는 `/dobot_TCP` 실측값을 사용한다.",
            "- z는 현장 결정에 따라 기본 -50mm로 고정 저장한다. raw 캡처의 실제 z는 `measured_z`와 JSON `raw_captures.harvest_grid_full`에 남긴다.",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture all 9 Dobot harvest positions from /dobot_TCP and merge them into calibration JSON."
    )
    parser.add_argument("--tcp-topic", default="/dobot_TCP", help="PoseStamped TCP pose topic")
    parser.add_argument("--raw-topic", default="/dobot_pose_raw", help="Optional Float64MultiArray raw pose topic")
    parser.add_argument("--positions", default=str(default_positions_path()), help="Calibration JSON to update")
    parser.add_argument("--harvest-z-mm", type=float, default=DEFAULT_HARVEST_Z_MM, help="Fixed harvest z to write, in mm")
    parser.add_argument("--initial-timeout", type=float, default=10.0, help="Seconds to wait for first TCP pose")
    parser.add_argument("--max-pose-age", type=float, default=1.0, help="Reject snapshots older than this many seconds")
    parser.add_argument("--no-backup", action="store_true", help="Do not create a backup before overwriting")
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
        node_name="dobot_harvest_position_calibrator",
        tcp_topic=args.tcp_topic,
        raw_topic=args.raw_topic,
    )
    capture_node.start()

    output_path = Path(args.positions).expanduser().resolve()
    captures: Dict[str, Dict[str, Any]] = {}

    try:
        print("/dobot_TCP 첫 pose 수신 대기 중...")
        if not wait_for_first_pose(capture_node, args.initial_timeout):
            print(f"ERROR: {args.initial_timeout}초 동안 {args.tcp_topic} pose를 받지 못했습니다.", file=sys.stderr)
            print("magician_ros2 bringup, homing, /dobot_TCP 토픽을 확인하세요.", file=sys.stderr)
            return 1

        print("\n수확 위치 9개를 모두 캡처합니다.")
        print("인덱스 기준: x 내림차순 -> y 내림차순")
        print(f"저장 z 값: {args.harvest_z_mm:.1f} mm (x/y만 실측값 사용)")

        harvest_grid: List[Dict[str, Any]] = []
        for index, key, label, instruction in HARVEST_CAPTURE_STEPS:
            capture = prompt_capture(
                capture_node,
                key=key,
                label=label,
                instruction=instruction,
                max_pose_age_sec=args.max_pose_age,
            )
            captures[key] = capture
            harvest_grid.append(capture_to_harvest_item(index, key, capture, args.harvest_z_mm))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        base = load_base_positions(output_path)
        backup_path = None if args.no_backup else backup_existing(output_path)
        result = build_result(
            base=base,
            captures=captures,
            harvest_grid=harvest_grid,
            tcp_topic=args.tcp_topic,
            raw_topic=args.raw_topic,
            harvest_z_mm=args.harvest_z_mm,
        )
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        print("\n저장 완료:")
        print(f"- JSON: {output_path}")
        if backup_path is not None:
            print(f"- Backup: {backup_path}")
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

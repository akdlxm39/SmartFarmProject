#!/usr/bin/env python3
"""
Conveyor top-view + ROI coordinate selector.

Workflow
1. Load one frame from ROS Image topic/image/video/camera.
2. MouseEvent1: click 4 points on the original frame for perspective transform.
3. Show the warped top-view frame.
4. MouseEvent2: click 4 points on the top-view frame for conveyor ROI.
5. Save machine-readable JSON and preview images.

Recommended click order: top-left -> top-right -> bottom-right -> bottom-left.
The script still normalizes the 4 points into TL/TR/BR/BL before saving.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np


WINDOW_ORIGINAL = "1_original_frame__click_4_points_for_topview"
WINDOW_TOPVIEW = "2_topview_frame__click_4_points_for_conveyor_roi"


@dataclass
class ClickState:
    points: list[list[int]] = field(default_factory=list)
    max_points: int = 4
    done: bool = False

    def add(self, x: int, y: int) -> None:
        if len(self.points) < self.max_points:
            self.points.append([int(x), int(y)])
        if len(self.points) >= self.max_points:
            self.done = True

    def undo(self) -> None:
        if self.points:
            self.points.pop()
        self.done = False

    def reset(self) -> None:
        self.points.clear()
        self.done = False


class AppContext:
    """Mutable context shared with OpenCV mouse callbacks."""

    def __init__(self, display_scale: float) -> None:
        self.display_scale = display_scale
        self.topview_state = ClickState()
        self.roi_state = ClickState()

    def display_to_image_xy(self, x: int, y: int) -> tuple[int, int]:
        if self.display_scale <= 0:
            raise ValueError("display_scale must be positive")
        return int(round(x / self.display_scale)), int(round(y / self.display_scale))


# ---------------------------------------------------------------------------
# Mouse callbacks requested by the user
# ---------------------------------------------------------------------------

def mouse_event_1_topview_quad(event: int, x: int, y: int, _flags: int, param: AppContext) -> None:
    """마우스이벤트1: original frame에서 상단뷰 변환용 4개 좌표를 받는다."""
    cv2 = import_cv2()
    if event == cv2.EVENT_LBUTTONDOWN:
        ix, iy = param.display_to_image_xy(x, y)
        param.topview_state.add(ix, iy)
        print(f"[MouseEvent1] topview point {len(param.topview_state.points)}/4: ({ix}, {iy})")
    elif event == cv2.EVENT_RBUTTONDOWN:
        param.topview_state.undo()
        print(f"[MouseEvent1] undo -> {len(param.topview_state.points)}/4 points")


def mouse_event_2_conveyor_roi(event: int, x: int, y: int, _flags: int, param: AppContext) -> None:
    """마우스이벤트2: top-view frame에서 컨베이어 ROI 4개 좌표를 받는다."""
    cv2 = import_cv2()
    if event == cv2.EVENT_LBUTTONDOWN:
        ix, iy = param.display_to_image_xy(x, y)
        param.roi_state.add(ix, iy)
        print(f"[MouseEvent2] roi point {len(param.roi_state.points)}/4: ({ix}, {iy})")
    elif event == cv2.EVENT_RBUTTONDOWN:
        param.roi_state.undo()
        print(f"[MouseEvent2] undo -> {len(param.roi_state.points)}/4 points")


# Short aliases matching the Korean step names in the project notes.
마우스이벤트1 = mouse_event_1_topview_quad
마우스이벤트2 = mouse_event_2_conveyor_roi


def import_cv2():
    try:
        import cv2  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "OpenCV(cv2)가 설치되어 있지 않습니다.\n"
            "작업환경에서 아래 명령을 먼저 실행하세요:\n"
            "  uv venv .venv\n"
            "  source .venv/bin/activate\n"
            "  uv pip install -r requirements.txt\n"
        ) from exc
    return cv2


def project_root_from(path: Path) -> Path:
    for candidate in [path, *path.parents]:
        if (candidate / "references" / "realsense-test-image.png").exists():
            return candidate
    # Fallback for this known workspace layout:
    return Path("/home/ssafy/work/SmartFarmProject")


def default_sample_image() -> Path:
    root = project_root_from(Path(__file__).resolve())
    return root / "references" / "realsense-test-image.png"


def click_order_points_tl_tr_br_bl(points: Iterable[Iterable[float]]) -> np.ndarray:
    """Use the operator's click order as TL -> TR -> BR -> BL."""
    pts = np.asarray(list(points), dtype="float32")
    if pts.shape != (4, 2):
        raise ValueError(f"Expected exactly four [x, y] points, got shape {pts.shape}")
    if len({tuple(map(float, p)) for p in pts}) != 4:
        raise ValueError("The 4 clicked points must be unique.")
    return pts


def auto_order_points_tl_tr_br_bl(points: Iterable[Iterable[float]]) -> np.ndarray:
    pts = click_order_points_tl_tr_br_bl(points)

    # Standard perspective ordering: TL has smallest sum, BR largest sum,
    # TR has smallest diff(x-y), BL largest diff(x-y).
    rect = np.zeros((4, 2), dtype="float32")
    sums = pts.sum(axis=1)
    diffs = np.diff(pts, axis=1).reshape(-1)

    rect[0] = pts[np.argmin(sums)]  # top-left
    rect[2] = pts[np.argmax(sums)]  # bottom-right
    rect[1] = pts[np.argmin(diffs)]  # top-right
    rect[3] = pts[np.argmax(diffs)]  # bottom-left

    if len({tuple(map(float, p)) for p in rect}) != 4:
        raise ValueError(
            "Could not uniquely order the 4 points. "
            "Click in TL -> TR -> BR -> BL order and avoid self-crossed quads."
        )
    return rect


def order_points_tl_tr_br_bl(points: Iterable[Iterable[float]], order_mode: str = "click") -> np.ndarray:
    if order_mode == "click":
        return click_order_points_tl_tr_br_bl(points)
    if order_mode == "auto":
        return auto_order_points_tl_tr_br_bl(points)
    raise ValueError(f"Unsupported point order mode: {order_mode}")


def expand_quad_from_center(rect: np.ndarray, padding_ratio: float) -> np.ndarray:
    """Expand a TL/TR/BR/BL quad around its center.

    Use this only when the top-view output looks slightly clipped versus the
    operator-selected area. Example: 0.03 expands the quad by 3% from center.
    """
    if padding_ratio == 0:
        return rect
    center = np.mean(rect, axis=0)
    return center + (rect - center) * (1.0 + float(padding_ratio))


def topview_size_from_quad(
    rect: np.ndarray,
    override_width: int | None,
    override_height: int | None,
    *,
    raw_width: int,
    raw_height: int,
    size_mode: str,
) -> tuple[int, int]:
    tl, tr, br, bl = rect
    width_top = np.linalg.norm(tr - tl)
    width_bottom = np.linalg.norm(br - bl)
    height_right = np.linalg.norm(br - tr)
    height_left = np.linalg.norm(bl - tl)

    quad_width = int(round(max(width_top, width_bottom)))
    quad_height = int(round(max(height_right, height_left)))

    if size_mode == "raw":
        # Default for this project: keep the warped top-view frame large enough
        # to click ROI comfortably and match the ROS frame scale. The old quad
        # mode made the output as small as the clicked source quad, which looked
        # like only a tiny frame appeared after selecting the top-view points.
        width = raw_width
        height = raw_height
    elif size_mode == "quad":
        width = quad_width
        height = quad_height
    else:
        raise ValueError(f"Unsupported topview size mode: {size_mode}")

    if override_width is not None:
        width = override_width
    if override_height is not None:
        height = override_height

    width = max(width, 1)
    height = max(height, 1)
    return width, height


def warp_topview(
    frame: np.ndarray,
    src_quad: Iterable[Iterable[float]],
    width: int | None = None,
    height: int | None = None,
    size_mode: str = "raw",
    point_order: str = "click",
    source_padding_ratio: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    cv2 = import_cv2()
    rect = order_points_tl_tr_br_bl(src_quad, point_order)
    rect = expand_quad_from_center(rect, source_padding_ratio)
    raw_h, raw_w = frame.shape[:2]
    out_w, out_h = topview_size_from_quad(
        rect,
        width,
        height,
        raw_width=raw_w,
        raw_height=raw_h,
        size_mode=size_mode,
    )
    dst = np.array(
        [[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(frame, matrix, (out_w, out_h))
    return warped, rect, matrix


def roi_xyxy_from_quad(roi_quad: Iterable[Iterable[float]]) -> list[int]:
    pts = np.asarray(list(roi_quad), dtype="float32")
    x_min = int(math.floor(float(np.min(pts[:, 0]))))
    y_min = int(math.floor(float(np.min(pts[:, 1]))))
    x_max = int(math.ceil(float(np.max(pts[:, 0]))))
    y_max = int(math.ceil(float(np.max(pts[:, 1]))))
    return [x_min, y_min, x_max, y_max]


def scale_for_display(image: np.ndarray, display_scale: float) -> np.ndarray:
    cv2 = import_cv2()
    if display_scale == 1.0:
        return image.copy()
    return cv2.resize(image, None, fx=display_scale, fy=display_scale, interpolation=cv2.INTER_AREA)


def draw_points(image: np.ndarray, points: list[list[int]], title: str, color: tuple[int, int, int]) -> np.ndarray:
    cv2 = import_cv2()
    canvas = image.copy()
    for idx, (x, y) in enumerate(points, start=1):
        cv2.circle(canvas, (int(x), int(y)), 6, color, -1)
        cv2.putText(canvas, str(idx), (int(x) + 8, int(y) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    if len(points) >= 2:
        for a, b in zip(points, points[1:]):
            cv2.line(canvas, tuple(a), tuple(b), color, 2)
    if len(points) == 4:
        cv2.line(canvas, tuple(points[3]), tuple(points[0]), color, 2)
    cv2.putText(canvas, title, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    return canvas


def annotate_result(raw_frame: np.ndarray, topview: np.ndarray, raw_quad: np.ndarray, roi_quad: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    raw_annotated = draw_points(raw_frame, raw_quad.astype(int).tolist(), "topview quad", (0, 255, 255))
    top_annotated = draw_points(topview, roi_quad.astype(int).tolist(), "conveyor roi", (0, 255, 0))
    return raw_annotated, top_annotated


def image_msg_to_bgr_numpy(msg: Any) -> np.ndarray:
    """Convert a ROS sensor_msgs/Image message to a BGR OpenCV frame without cv_bridge.

    This keeps the calibration helper easy to run in mixed ROS/venv setups.
    Supported encodings cover common RealSense color topics: bgr8, rgb8, bgra8,
    rgba8, mono8, 8UC3, and 8UC1.
    """
    cv2 = import_cv2()
    encoding = (msg.encoding or "").lower()
    height = int(msg.height)
    width = int(msg.width)
    step = int(msg.step)
    raw = np.frombuffer(msg.data, dtype=np.uint8)

    if encoding in {"bgr8", "rgb8", "8uc3"}:
        channels = 3
        expected_step_min = width * channels
        if step < expected_step_min:
            raise ValueError(f"Invalid ROS Image step={step} for {width}x{height} {encoding}")
        arr = raw.reshape((height, step))[:, :expected_step_min].reshape((height, width, channels))
        if msg.is_bigendian:
            arr = arr.byteswap()
        if encoding == "rgb8":
            return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        return arr.copy()

    if encoding in {"bgra8", "rgba8", "8uc4"}:
        channels = 4
        expected_step_min = width * channels
        if step < expected_step_min:
            raise ValueError(f"Invalid ROS Image step={step} for {width}x{height} {encoding}")
        arr = raw.reshape((height, step))[:, :expected_step_min].reshape((height, width, channels))
        if encoding == "rgba8":
            return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)

    if encoding in {"mono8", "8uc1"}:
        expected_step_min = width
        if step < expected_step_min:
            raise ValueError(f"Invalid ROS Image step={step} for {width}x{height} {encoding}")
        arr = raw.reshape((height, step))[:, :expected_step_min].reshape((height, width))
        return cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)

    raise ValueError(
        f"Unsupported ROS Image encoding: {msg.encoding!r}. "
        "Use a color topic like /camera/camera/color/image_raw with rgb8/bgr8."
    )


def load_frame_from_ros_topic(args: argparse.Namespace) -> tuple[np.ndarray, dict[str, Any]]:
    cv2 = import_cv2()
    try:
        import rclpy  # type: ignore
        from rclpy.node import Node  # type: ignore
        from sensor_msgs.msg import Image  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "ROS2 Python 패키지(rclpy/sensor_msgs)를 import할 수 없습니다.\n"
            "ROS 환경을 source한 뒤 실행하세요. 예:\n"
            "  source /opt/ros/humble/setup.bash\n"
            "  cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/conveyor\n"
            "  source .venv/bin/activate\n"
            "  python scripts/select_conveyor_roi.py --ros-topic /camera/camera/color/image_raw\n"
        ) from exc

    latest_frame: np.ndarray | None = None
    latest_msg: Any | None = None
    latest_error: Exception | None = None

    class OneFrameNode(Node):
        def __init__(self) -> None:
            super().__init__("conveyor_roi_calibration_frame_grabber")
            self.create_subscription(Image, args.ros_topic, self.on_image, 10)

        def on_image(self, msg: Any) -> None:
            nonlocal latest_frame, latest_msg, latest_error
            try:
                latest_frame = image_msg_to_bgr_numpy(msg)
                latest_msg = msg
                latest_error = None
            except Exception as exc:  # Keep spinning but surface conversion errors.
                latest_error = exc

    rclpy.init(args=None)
    node = OneFrameNode()
    start_time = datetime.now(timezone.utc)
    print(f"ROS topic preview: {args.ros_topic}")
    print("- SPACE: 현재 ROS 프레임 고정 후 좌표 선택으로 이동")
    print("- q 또는 ESC: 종료")

    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.03)
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if latest_error is not None:
                raise SystemExit(f"ROS Image 변환 실패: {latest_error}")
            if elapsed > args.ros_timeout_sec and latest_frame is None:
                raise SystemExit(f"{args.ros_timeout_sec}s 동안 ROS Image를 받지 못했습니다: {args.ros_topic}")
            if latest_frame is not None:
                preview = latest_frame.copy()
                label = f"ROS {args.ros_topic} {preview.shape[1]}x{preview.shape[0]}  SPACE=freeze"
                cv2.putText(preview, label, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
                cv2.imshow("ros_topic_preview__press_SPACE_to_freeze", scale_for_display(preview, args.display_scale))
            key = cv2.waitKey(1) & 0xFF
            if key == ord(" ") and latest_frame is not None:
                frame = latest_frame.copy()
                msg = latest_msg
                cv2.destroyWindow("ros_topic_preview__press_SPACE_to_freeze")
                source_meta = {
                    "source_type": "ros_topic",
                    "topic": args.ros_topic,
                    "encoding": getattr(msg, "encoding", None),
                    "width": int(getattr(msg, "width", frame.shape[1])),
                    "height": int(getattr(msg, "height", frame.shape[0])),
                    "step": int(getattr(msg, "step", 0)),
                    "frame_id": getattr(getattr(msg, "header", None), "frame_id", ""),
                    "stamp": {
                        "sec": int(getattr(getattr(getattr(msg, "header", None), "stamp", None), "sec", 0)),
                        "nanosec": int(getattr(getattr(getattr(msg, "header", None), "stamp", None), "nanosec", 0)),
                    },
                    "calibration_method": "live_ros_frame_space_to_freeze",
                }
                return frame, source_meta
            if key in (ord("q"), 27):
                raise SystemExit("Cancelled")
    finally:
        node.destroy_node()
        rclpy.shutdown()

    raise SystemExit("ROS frame capture ended unexpectedly")


def load_frame_from_args(args: argparse.Namespace) -> tuple[np.ndarray, dict[str, Any]]:
    cv2 = import_cv2()
    if args.ros_topic is not None:
        return load_frame_from_ros_topic(args)

    if args.camera is not None:
        cap = cv2.VideoCapture(args.camera)
        if not cap.isOpened():
            raise SystemExit(f"Could not open camera index {args.camera}")
        print("Camera preview: SPACE=현재 프레임 고정, q=종료")
        frame = None
        while True:
            ok, current = cap.read()
            if not ok:
                cap.release()
                raise SystemExit("Could not read frame from camera")
            cv2.imshow("camera_preview__press_SPACE_to_freeze", current)
            key = cv2.waitKey(1) & 0xFF
            if key == ord(" "):
                frame = current.copy()
                break
            if key in (ord("q"), 27):
                cap.release()
                raise SystemExit("Cancelled")
        cap.release()
        cv2.destroyWindow("camera_preview__press_SPACE_to_freeze")
        return frame, {"source_type": "camera", "camera_index": args.camera, "calibration_method": "opencv_camera_space_to_freeze"}

    if args.video is not None:
        cap = cv2.VideoCapture(str(args.video))
        if not cap.isOpened():
            raise SystemExit(f"Could not open video: {args.video}")
        ok, frame = cap.read()
        cap.release()
        if not ok:
            raise SystemExit(f"Could not read first frame from video: {args.video}")
        return frame, {"source_type": "video", "video_path": str(args.video)}

    image_path = Path(args.image).expanduser().resolve()
    frame = cv2.imread(str(image_path))
    if frame is None:
        raise SystemExit(f"Could not read image: {image_path}")
    return frame, {"source_type": "image", "image_path": str(image_path)}


def interactive_collect_quad(frame: np.ndarray, ctx: AppContext, window_name: str, state: ClickState, callback, title: str, color: tuple[int, int, int]) -> list[list[int]]:
    cv2 = import_cv2()
    # Use AUTOSIZE so OpenCV does not silently rescale the displayed image and
    # make mouse coordinates differ from actual image pixels. If the image is too
    # large for the monitor, pass --display-scale 0.7 etc.; we then scale the
    # image explicitly and convert mouse coordinates back ourselves.
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(window_name, callback, ctx)

    print(f"\n{title}")
    print("- 왼쪽 클릭: 점 추가")
    print("- 오른쪽 클릭 또는 u: 마지막 점 취소")
    print("- r: 현재 단계 점 초기화")
    print("- q 또는 ESC: 종료")
    print("권장 클릭 순서: 좌상단 -> 우상단 -> 우하단 -> 좌하단")

    while not state.done:
        annotated = draw_points(frame, state.points, f"{title}: {len(state.points)}/4", color)
        cv2.imshow(window_name, scale_for_display(annotated, ctx.display_scale))
        key = cv2.waitKey(20) & 0xFF
        if key in (ord("q"), 27):
            raise SystemExit("Cancelled")
        if key == ord("u"):
            state.undo()
        if key == ord("r"):
            state.reset()

    annotated = draw_points(frame, state.points, f"{title}: done", color)
    cv2.imshow(window_name, scale_for_display(annotated, ctx.display_scale))
    cv2.waitKey(300)
    cv2.destroyWindow(window_name)
    return state.points.copy()


def save_outputs(
    args: argparse.Namespace,
    frame: np.ndarray,
    source_meta: dict[str, Any],
    topview: np.ndarray,
    raw_quad_ordered: np.ndarray,
    roi_quad_ordered: np.ndarray,
    matrix: np.ndarray,
) -> Path:
    cv2 = import_cv2()
    output_json = Path(args.output).expanduser().resolve()
    output_json.parent.mkdir(parents=True, exist_ok=True)

    raw_annotated, top_annotated = annotate_result(frame, topview, raw_quad_ordered, roi_quad_ordered)
    preview_dir = output_json.parent / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    stem = output_json.stem
    raw_preview = preview_dir / f"{stem}_raw_topview_quad.png"
    topview_preview = preview_dir / f"{stem}_topview_roi.png"
    topview_image = preview_dir / f"{stem}_topview.png"
    cv2.imwrite(str(raw_preview), raw_annotated)
    cv2.imwrite(str(topview_preview), top_annotated)
    cv2.imwrite(str(topview_image), topview)

    result = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "SmartFarmProject conveyor top-view and single ROI calibration",
        "source": source_meta,
        "raw_frame": {"width": int(frame.shape[1]), "height": int(frame.shape[0]), "channels": int(frame.shape[2]) if frame.ndim == 3 else 1},
        "topview": {
            "enabled": True,
            "source_quad_raw_xy_tl_tr_br_bl": raw_quad_ordered.astype(int).tolist(),
            "size_wh": [int(topview.shape[1]), int(topview.shape[0])],
            "output_size_mode": args.topview_size_mode,
            "point_order_mode": args.point_order,
            "source_padding_ratio": args.source_padding_ratio,
            "perspective_matrix_raw_to_topview": matrix.tolist(),
        },
        "conveyor_roi": {
            "coordinate_space": "topview",
            "quad_xy_tl_tr_br_bl": roi_quad_ordered.astype(int).tolist(),
            "xyxy": roi_xyxy_from_quad(roi_quad_ordered),
        },
        "runtime_defaults": {
            "cube_colors": ["red", "green"],
            "red_green_same_meaning": True,
            "disappear_stable_frames": 10,
            "motor_direction": "clockwise",
            "modbus": {"mode": "tcp", "library": "pymodbus==3.13.1"},
        },
        "preview_files": {
            "raw_topview_quad": str(raw_preview),
            "topview_roi": str(topview_preview),
            "topview_image": str(topview_image),
        },
        "notes": [
            "Use conveyor_roi.xyxy or conveyor_roi.quad_xy_tl_tr_br_bl for OpenCV detection in the warped top-view frame.",
            "If the camera position changes, rerun this selector and overwrite/regenerate the JSON.",
        ],
    }
    with output_json.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return output_json


def self_test(args: argparse.Namespace) -> Path:
    """Non-GUI smoke test for CI/headless verification."""
    frame, source_meta = load_frame_from_args(args)
    h, w = frame.shape[:2]
    margin_x = max(10, int(w * 0.15))
    margin_y = max(10, int(h * 0.10))
    raw_quad = np.array(
        [
            [margin_x, margin_y],
            [w - margin_x - 1, margin_y],
            [w - margin_x - 1, h - margin_y - 1],
            [margin_x, h - margin_y - 1],
        ],
        dtype="float32",
    )
    topview, raw_ordered, matrix = warp_topview(
        frame,
        raw_quad,
        args.topview_width,
        args.topview_height,
        size_mode=args.topview_size_mode,
        point_order=args.point_order,
        source_padding_ratio=args.source_padding_ratio,
    )
    th, tw = topview.shape[:2]
    roi_quad = np.array(
        [
            [int(tw * 0.20), int(th * 0.15)],
            [int(tw * 0.80), int(th * 0.15)],
            [int(tw * 0.80), int(th * 0.85)],
            [int(tw * 0.20), int(th * 0.85)],
        ],
        dtype="float32",
    )
    roi_ordered = order_points_tl_tr_br_bl(roi_quad, args.point_order)
    return save_outputs(args, frame, source_meta, topview, raw_ordered, roi_ordered, matrix)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OpenCV GUI tool for selecting conveyor top-view quad and ROI coordinates.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--image", type=Path, default=default_sample_image(), help="Image path to use as the calibration frame")
    source.add_argument("--ros-topic", default=None, help="ROS2 sensor_msgs/Image topic to use as the calibration frame. Press SPACE to freeze one live frame.")
    source.add_argument("--camera", type=int, help="OpenCV camera index. Press SPACE to freeze one frame.")
    source.add_argument("--video", type=Path, help="Video path. Uses the first frame.")
    parser.add_argument("--output", type=Path, default=Path("config/conveyor_roi_topview.json"), help="Output JSON path")
    parser.add_argument("--display-scale", type=float, default=1.0, help="Scale GUI display while saving original coordinates")
    parser.add_argument("--topview-width", type=int, default=None, help="Override warped top-view width")
    parser.add_argument("--topview-height", type=int, default=None, help="Override warped top-view height")
    parser.add_argument(
        "--topview-size-mode",
        choices=["raw", "quad"],
        default="raw",
        help="Top-view output size. raw keeps the warped top-view at the original ROS frame size; quad uses the clicked quadrilateral size.",
    )
    parser.add_argument(
        "--point-order",
        choices=["click", "auto"],
        default="click",
        help="How to order 4 clicked points. click trusts TL->TR->BR->BL click order; auto uses coordinate sorting.",
    )
    parser.add_argument(
        "--source-padding-ratio",
        type=float,
        default=0.0,
        help="Expand the selected top-view source quad from its center before warping. Try 0.02 or 0.03 if the output looks slightly clipped.",
    )
    parser.add_argument("--ros-timeout-sec", type=float, default=10.0, help="Timeout while waiting for the first ROS Image")
    parser.add_argument("--self-test", action="store_true", help="Run a non-interactive smoke test with generated points")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.display_scale <= 0:
        raise SystemExit("--display-scale must be positive")
    if args.source_padding_ratio < 0:
        raise SystemExit("--source-padding-ratio must be >= 0")

    if args.self_test:
        output_path = self_test(args)
        print(f"Self-test JSON saved: {output_path}")
        return 0

    cv2 = import_cv2()
    frame, source_meta = load_frame_from_args(args)
    ctx = AppContext(display_scale=args.display_scale)

    raw_quad_clicked = interactive_collect_quad(
        frame,
        ctx,
        WINDOW_ORIGINAL,
        ctx.topview_state,
        mouse_event_1_topview_quad,
        "MouseEvent1 / 상단뷰 변환 좌표 4점 선택",
        (0, 255, 255),
    )
    topview, raw_quad_ordered, matrix = warp_topview(
        frame,
        raw_quad_clicked,
        args.topview_width,
        args.topview_height,
        size_mode=args.topview_size_mode,
        point_order=args.point_order,
        source_padding_ratio=args.source_padding_ratio,
    )

    print(
        f"Top-view frame created: {topview.shape[1]}x{topview.shape[0]} "
        f"(size_mode={args.topview_size_mode}). "
        "이 창에서 컨베이어 ROI 4점을 찍으세요."
    )

    roi_clicked = interactive_collect_quad(
        topview,
        ctx,
        WINDOW_TOPVIEW,
        ctx.roi_state,
        mouse_event_2_conveyor_roi,
        "MouseEvent2 / 컨베이어 ROI 좌표 4점 선택",
        (0, 255, 0),
    )
    roi_quad_ordered = order_points_tl_tr_br_bl(roi_clicked, args.point_order)

    output_path = save_outputs(args, frame, source_meta, topview, raw_quad_ordered, roi_quad_ordered, matrix)
    print(f"\nSaved calibration JSON: {output_path}")
    print("Preview images are in:", output_path.parent / "previews")

    # Final confirmation window.
    _raw_annotated, top_annotated = annotate_result(frame, topview, raw_quad_ordered, roi_quad_ordered)
    cv2.imshow("result_topview_roi__press_any_key", scale_for_display(top_annotated, ctx.display_scale))
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

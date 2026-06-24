"""ROS2 test node for conveyor top-view ROI red/green detection."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Image

from conveyor_vision_test.conveyor_modbus import (
    COMMAND_EMERGENCY_STOP,
    COMMAND_STOP,
    ConveyorModbusTcpClient,
    ConveyorRegisterState,
    ConveyorVisionStateMachine,
    build_command_write_plan,
    command_name,
    format_register_state,
    parse_conveyor_command,
)

DEFAULT_CONFIG_PATH = (
    "/home/ssafy/work/SmartFarmProject/workspaces/지웅/conveyor/"
    "config/conveyor_roi_topview.json"
)

ColorDetection = Dict[str, object]
Point = Tuple[int, int]


def load_roi_config(config_path: str) -> Dict[str, object]:
    """Load conveyor top-view calibration JSON."""
    path = Path(config_path).expanduser()
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _as_int_points(points: Sequence[Sequence[float]]) -> np.ndarray:
    return np.array([[int(round(x)), int(round(y))] for x, y in points], dtype=np.int32)


def polygon_from_config(config: Dict[str, object]) -> Optional[np.ndarray]:
    """Return conveyor ROI polygon in top-view coordinates."""
    conveyor_roi = config.get("conveyor_roi", {})
    if not isinstance(conveyor_roi, dict):
        return None

    quad = conveyor_roi.get("quad_xy_tl_tr_br_bl")
    if isinstance(quad, list) and len(quad) >= 3:
        return _as_int_points(quad)

    xyxy = conveyor_roi.get("xyxy")
    if isinstance(xyxy, list) and len(xyxy) == 4:
        x1, y1, x2, y2 = [int(round(v)) for v in xyxy]
        return np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.int32)

    return None


def topview_size_from_config(config: Dict[str, object]) -> Tuple[int, int]:
    topview = config.get("topview", {})
    if not isinstance(topview, dict):
        raise ValueError("config.topview is missing")

    size_wh = topview.get("size_wh")
    if not isinstance(size_wh, list) or len(size_wh) != 2:
        raise ValueError("config.topview.size_wh must be [width, height]")
    return int(size_wh[0]), int(size_wh[1])


def perspective_matrix_from_config(config: Dict[str, object]) -> np.ndarray:
    topview = config.get("topview", {})
    if not isinstance(topview, dict):
        raise ValueError("config.topview is missing")

    matrix = topview.get("perspective_matrix_raw_to_topview")
    if not isinstance(matrix, list):
        raise ValueError("config.topview.perspective_matrix_raw_to_topview is missing")
    return np.array(matrix, dtype=np.float32)


def raw_size_from_config(config: Dict[str, object]) -> Optional[Tuple[int, int]]:
    raw_frame = config.get("raw_frame", {})
    if isinstance(raw_frame, dict) and "width" in raw_frame and "height" in raw_frame:
        return int(raw_frame["width"]), int(raw_frame["height"])
    source = config.get("source", {})
    if isinstance(source, dict) and "width" in source and "height" in source:
        return int(source["width"]), int(source["height"])
    return None


def ros_image_to_bgr(msg: Image) -> np.ndarray:
    """Convert common sensor_msgs/Image encodings to an OpenCV BGR image."""
    encoding = msg.encoding.lower()
    data = np.frombuffer(msg.data, dtype=np.uint8)

    if encoding in {"rgb8", "bgr8", "8uc3"}:
        channels = 3
        rows = data.reshape((msg.height, msg.step))
        packed = rows[:, : msg.width * channels]
        image = packed.reshape((msg.height, msg.width, channels))
        if encoding == "rgb8":
            return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        return image.copy()

    if encoding in {"rgba8", "bgra8", "8uc4"}:
        channels = 4
        rows = data.reshape((msg.height, msg.step))
        packed = rows[:, : msg.width * channels]
        image = packed.reshape((msg.height, msg.width, channels))
        if encoding == "rgba8":
            return cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

    if encoding in {"mono8", "8uc1"}:
        rows = data.reshape((msg.height, msg.step))
        gray = rows[:, : msg.width]
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    if encoding in {"yuyv", "yuv422_yuy2"}:
        rows = data.reshape((msg.height, msg.step))
        packed = rows[:, : msg.width * 2]
        yuyv = packed.reshape((msg.height, msg.width, 2))
        return cv2.cvtColor(yuyv, cv2.COLOR_YUV2BGR_YUY2)

    raise ValueError(f"Unsupported image encoding: {msg.encoding}")


def bgr_to_ros_image(bgr: np.ndarray, source_msg: Image, frame_suffix: str = "_topview") -> Image:
    """Create sensor_msgs/Image from a BGR OpenCV image."""
    contiguous = np.ascontiguousarray(bgr)
    out = Image()
    out.header = source_msg.header
    if out.header.frame_id:
        out.header.frame_id = f"{out.header.frame_id}{frame_suffix}"
    else:
        out.header.frame_id = "conveyor_topview"
    out.height = int(contiguous.shape[0])
    out.width = int(contiguous.shape[1])
    out.encoding = "bgr8"
    out.is_bigendian = 0
    out.step = int(contiguous.shape[1] * 3)
    out.data = contiguous.tobytes()
    return out


def make_roi_mask(shape_hw: Tuple[int, int], roi_polygon: Optional[np.ndarray]) -> np.ndarray:
    """Create a uint8 mask for the configured conveyor ROI."""
    height, width = shape_hw
    mask = np.zeros((height, width), dtype=np.uint8)
    if roi_polygon is None:
        mask[:, :] = 255
    else:
        cv2.fillPoly(mask, [roi_polygon.astype(np.int32)], 255)
    return mask


def detect_red_green_objects(
    bgr: np.ndarray,
    roi_polygon: Optional[np.ndarray],
    min_area: float = 250.0,
    morph_kernel_size: int = 5,
) -> List[ColorDetection]:
    """Detect red and green blobs inside the top-view ROI."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    roi_mask = make_roi_mask(bgr.shape[:2], roi_polygon)

    red_mask_1 = cv2.inRange(hsv, np.array([0, 80, 50]), np.array([10, 255, 255]))
    red_mask_2 = cv2.inRange(hsv, np.array([170, 80, 50]), np.array([180, 255, 255]))
    masks = {
        "red": cv2.bitwise_or(red_mask_1, red_mask_2),
        "green": cv2.inRange(hsv, np.array([35, 60, 40]), np.array([90, 255, 255])),
    }

    kernel = None
    if morph_kernel_size > 1:
        kernel = np.ones((morph_kernel_size, morph_kernel_size), dtype=np.uint8)

    detections: List[ColorDetection] = []
    for color_name, color_mask in masks.items():
        masked = cv2.bitwise_and(color_mask, roi_mask)
        if kernel is not None:
            masked = cv2.morphologyEx(masked, cv2.MORPH_OPEN, kernel)
            masked = cv2.morphologyEx(masked, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(masked, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = float(cv2.contourArea(contour))
            if area < min_area:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            detections.append(
                {
                    "color": color_name,
                    "bbox_xyxy": (int(x), int(y), int(x + w), int(y + h)),
                    "area": area,
                }
            )

    detections.sort(key=lambda item: (str(item["color"]), -float(item["area"])))
    return detections


def draw_roi_and_detections(
    topview_bgr: np.ndarray,
    roi_polygon: Optional[np.ndarray],
    detections: Sequence[ColorDetection],
) -> np.ndarray:
    """Draw ROI outline and detection bounding boxes."""
    annotated = topview_bgr.copy()

    if roi_polygon is not None:
        overlay = annotated.copy()
        cv2.fillPoly(overlay, [roi_polygon.astype(np.int32)], (0, 255, 255))
        annotated = cv2.addWeighted(overlay, 0.12, annotated, 0.88, 0)
        cv2.polylines(annotated, [roi_polygon.astype(np.int32)], True, (0, 255, 255), 2)
        label_point = tuple(roi_polygon.astype(np.int32)[0])
        cv2.putText(
            annotated,
            "ROI",
            label_point,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )

    for detection in detections:
        color_name = str(detection["color"])
        x1, y1, x2, y2 = detection["bbox_xyxy"]  # type: ignore[index]
        box_color = (0, 0, 255) if color_name == "red" else (0, 255, 0)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, 2)
        text = f"{color_name} {float(detection['area']):.0f}"
        cv2.putText(
            annotated,
            text,
            (x1, max(20, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            box_color,
            2,
            cv2.LINE_AA,
        )

    return annotated


class ConveyorTopviewColorDetector(Node):
    """Subscribe to D435i color frames, warp top-view, and display ROI detections."""

    def __init__(self) -> None:
        super().__init__("conveyor_topview_color_detector")

        self.declare_parameter("image_topic", "/camera/camera/color/image_raw")
        self.declare_parameter("config_path", DEFAULT_CONFIG_PATH)
        self.declare_parameter("annotated_topic", "/conveyor/topview_annotated")
        self.declare_parameter("show_windows", True)
        self.declare_parameter("publish_annotated", True)
        self.declare_parameter("display_scale", 1.0)
        self.declare_parameter("min_area", 250.0)
        self.declare_parameter("morph_kernel_size", 5)
        self.declare_parameter("allow_dimension_mismatch", False)
        self.declare_parameter("disappear_stable_frames", 10)
        self.declare_parameter("modbus_enabled", False)
        self.declare_parameter("modbus_host", "192.168.110.109")
        self.declare_parameter("modbus_port", 50200)
        self.declare_parameter("modbus_unit_id", 1)
        self.declare_parameter("modbus_timeout", 1.0)
        self.declare_parameter("modbus_zero_based_addresses", True)
        self.declare_parameter("modbus_dry_run", False)
        self.declare_parameter("conveyor_run_command", "run_clockwise")
        self.declare_parameter("conveyor_speed_cmd", 100)
        self.declare_parameter("modbus_write_initial_state", True)
        self.declare_parameter("modbus_shutdown_command", "stop")

        self.image_topic = str(self.get_parameter("image_topic").value)
        self.config_path = str(self.get_parameter("config_path").value)
        self.annotated_topic = str(self.get_parameter("annotated_topic").value)
        self.show_windows = bool(self.get_parameter("show_windows").value)
        self.publish_annotated = bool(self.get_parameter("publish_annotated").value)
        self.display_scale = float(self.get_parameter("display_scale").value)
        self.min_area = float(self.get_parameter("min_area").value)
        self.morph_kernel_size = int(self.get_parameter("morph_kernel_size").value)
        self.allow_dimension_mismatch = bool(
            self.get_parameter("allow_dimension_mismatch").value
        )
        self.disappear_stable_frames = int(self.get_parameter("disappear_stable_frames").value)
        self.modbus_enabled = bool(self.get_parameter("modbus_enabled").value)
        self.modbus_host = str(self.get_parameter("modbus_host").value)
        self.modbus_port = int(self.get_parameter("modbus_port").value)
        self.modbus_unit_id = int(self.get_parameter("modbus_unit_id").value)
        self.modbus_timeout = float(self.get_parameter("modbus_timeout").value)
        self.modbus_zero_based_addresses = bool(
            self.get_parameter("modbus_zero_based_addresses").value
        )
        self.modbus_dry_run = bool(self.get_parameter("modbus_dry_run").value)
        self.conveyor_run_command = parse_conveyor_command(
            self.get_parameter("conveyor_run_command").value
        )
        self.conveyor_speed_cmd = int(self.get_parameter("conveyor_speed_cmd").value)
        self.modbus_write_initial_state = bool(
            self.get_parameter("modbus_write_initial_state").value
        )
        self.modbus_shutdown_command = parse_conveyor_command(
            self.get_parameter("modbus_shutdown_command").value
        )

        if self.show_windows and not os.environ.get("DISPLAY"):
            self.get_logger().warning("DISPLAY is not set; disabling OpenCV windows.")
            self.show_windows = False

        self.config = load_roi_config(self.config_path)
        self.raw_size = raw_size_from_config(self.config)
        self.topview_size = topview_size_from_config(self.config)
        self.matrix = perspective_matrix_from_config(self.config)
        self.roi_polygon = polygon_from_config(self.config)
        self.dimension_warning_logged = False
        self.last_detection_signature: Optional[Tuple[Tuple[str, Tuple[int, int, int, int]], ...]] = None
        self.vision_state_machine = ConveyorVisionStateMachine(
            disappear_stable_frames=self.disappear_stable_frames,
            run_command=self.conveyor_run_command,
            speed_cmd=self.conveyor_speed_cmd,
        )
        self.modbus_client: Optional[ConveyorModbusTcpClient] = None
        self.last_modbus_state: Optional[ConveyorRegisterState] = None
        if self.modbus_enabled:
            self.modbus_client = ConveyorModbusTcpClient(
                host=self.modbus_host,
                port=self.modbus_port,
                unit_id=self.modbus_unit_id,
                timeout=self.modbus_timeout,
                zero_based_addresses=self.modbus_zero_based_addresses,
                dry_run=self.modbus_dry_run,
            )

        self.publisher = None
        if self.publish_annotated:
            self.publisher = self.create_publisher(Image, self.annotated_topic, 10)

        self.subscription = self.create_subscription(Image, self.image_topic, self.on_image, 10)

        self.get_logger().info(f"Subscribed image_topic={self.image_topic}")
        self.get_logger().info(f"Loaded ROI config={self.config_path}")
        self.get_logger().info(
            f"Top-view size={self.topview_size}, raw calibration size={self.raw_size}"
        )
        self.get_logger().info(
            "OpenCV window: " + ("enabled" if self.show_windows else "disabled")
        )
        self.get_logger().info(
            "Modbus: "
            + (
                f"enabled target={self.modbus_host}:{self.modbus_port} "
                f"unit_id={self.modbus_unit_id} run_command="
                f"{command_name(self.conveyor_run_command)} speed={self.conveyor_speed_cmd}"
                if self.modbus_enabled
                else "disabled"
            )
        )
        if self.modbus_enabled and self.modbus_write_initial_state:
            self._write_modbus_state(self.vision_state_machine.idle_state(), force=True)

    def _write_modbus_state(self, state: ConveyorRegisterState, force: bool = False) -> None:
        if not self.modbus_enabled or self.modbus_client is None:
            return
        if not force and state == self.last_modbus_state:
            return
        try:
            physical_state = self.modbus_client.read_physical_state()
            plan = build_command_write_plan(state, physical_state)
            ok = self.modbus_client.write_command_plan(plan)
        except RuntimeError as exc:
            self.get_logger().error(str(exc))
            return
        if ok:
            self.last_modbus_state = state
            extra = f"; {plan.skip_reason}" if plan.skip_reason else ""
            self.get_logger().info("Modbus write: " + format_register_state(state) + extra)
        else:
            self.get_logger().error("Modbus write failed: " + format_register_state(state))

    def _send_shutdown_command(self) -> None:
        if not self.modbus_enabled or self.modbus_client is None:
            return
        if self.modbus_shutdown_command == COMMAND_EMERGENCY_STOP:
            state = self.vision_state_machine.emergency_stop_state()
            self._write_modbus_state(state, force=True)
        elif self.modbus_shutdown_command == COMMAND_STOP:
            state = self.vision_state_machine.idle_state()
            self._write_modbus_state(state, force=True)

    def on_image(self, msg: Image) -> None:
        if self.raw_size and (msg.width, msg.height) != self.raw_size:
            if not self.dimension_warning_logged:
                self.get_logger().error(
                    "Live frame size does not match calibration JSON: "
                    f"live=({msg.width}, {msg.height}) config={self.raw_size}. "
                    "Rerun select_conveyor_roi.py or set "
                    "allow_dimension_mismatch:=true only for temporary testing."
                )
                self.dimension_warning_logged = True
            if not self.allow_dimension_mismatch:
                return

        try:
            frame_bgr = ros_image_to_bgr(msg)
        except ValueError as exc:
            self.get_logger().error(str(exc))
            return

        topview = cv2.warpPerspective(frame_bgr, self.matrix, self.topview_size)
        detections = detect_red_green_objects(
            topview,
            self.roi_polygon,
            min_area=self.min_area,
            morph_kernel_size=self.morph_kernel_size,
        )
        modbus_state = self.vision_state_machine.update(detections)
        self._write_modbus_state(modbus_state)
        annotated = draw_roi_and_detections(topview, self.roi_polygon, detections)

        signature = tuple(
            (str(item["color"]), tuple(item["bbox_xyxy"])) for item in detections
        )
        if signature != self.last_detection_signature:
            self.last_detection_signature = signature
            summary = ", ".join(
                f"{item['color']}@{item['bbox_xyxy']} area={float(item['area']):.0f}"
                for item in detections
            )
            self.get_logger().info(
                f"detections={len(detections)}" + (f" [{summary}]" if summary else "")
            )

        if self.publisher is not None:
            self.publisher.publish(bgr_to_ros_image(annotated, msg))

        if self.show_windows:
            shown = annotated
            if self.display_scale > 0 and abs(self.display_scale - 1.0) > 1e-6:
                shown = cv2.resize(
                    annotated,
                    None,
                    fx=self.display_scale,
                    fy=self.display_scale,
                    interpolation=cv2.INTER_AREA,
                )
            cv2.imshow("conveyor_topview_roi_detector", shown)
            key = cv2.waitKey(1) & 0xFF
            if key in {ord("q"), 27}:
                self.get_logger().info("Quit key received; shutting down.")
                rclpy.shutdown()

    def destroy_node(self) -> bool:
        self._send_shutdown_command()
        if self.modbus_client is not None:
            self.modbus_client.close()
        if self.show_windows:
            cv2.destroyAllWindows()
        return super().destroy_node()


def main(args: Optional[Sequence[str]] = None) -> None:
    rclpy.init(args=args)
    node = ConveyorTopviewColorDetector()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

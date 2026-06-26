#!/usr/bin/env python3
"""
Conveyor raw-view ROI coordinate selector.

이 스크립트는 D435i/ROS color raw frame에서 top-view 변환 없이 바로
컨베이어 ROI 4점을 찍어 config/conveyor_roi_raw.json을 갱신한다.

Workflow
1. ROS Image topic / image / video / OpenCV camera에서 한 프레임을 불러온다.
2. raw view 화면에서 컨베이어 ROI 4점을 클릭한다.
3. raw-frame 좌표계 기준 JSON과 preview 이미지를 저장한다.

권장 클릭 순서: 좌상단 -> 우상단 -> 우하단 -> 좌하단.
기본 point-order는 click이라 클릭 순서를 그대로 TL/TR/BR/BL로 저장한다.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

# 같은 scripts/ 폴더의 기존 frame grabber / drawing utility를 재사용한다.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from select_conveyor_roi import (  # noqa: E402
    AppContext,
    ClickState,
    default_sample_image,
    draw_points,
    import_cv2,
    load_frame_from_args,
    order_points_tl_tr_br_bl,
    roi_xyxy_from_quad,
    scale_for_display,
)

WINDOW_RAW_ROI = "raw_view__click_4_points_for_conveyor_roi"


class RawRoiContext(AppContext):
    """Mouse callback context for raw ROI selection."""

    def __init__(self, display_scale: float) -> None:
        super().__init__(display_scale)
        self.raw_roi_state = ClickState()


def mouse_event_raw_conveyor_roi(event: int, x: int, y: int, _flags: int, param: RawRoiContext) -> None:
    """raw view에서 컨베이어 ROI 4개 좌표를 받는다."""

    cv2 = import_cv2()
    if event == cv2.EVENT_LBUTTONDOWN:
        ix, iy = param.display_to_image_xy(x, y)
        param.raw_roi_state.add(ix, iy)
        print(f"[RawROI] roi point {len(param.raw_roi_state.points)}/4: ({ix}, {iy})")
    elif event == cv2.EVENT_RBUTTONDOWN:
        param.raw_roi_state.undo()
        print(f"[RawROI] undo -> {len(param.raw_roi_state.points)}/4 points")


def interactive_collect_raw_roi(frame: np.ndarray, ctx: RawRoiContext) -> list[list[int]]:
    cv2 = import_cv2()
    cv2.namedWindow(WINDOW_RAW_ROI, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(WINDOW_RAW_ROI, mouse_event_raw_conveyor_roi, ctx)

    print("\nRaw view / 컨베이어 ROI 좌표 4점 선택")
    print("- 왼쪽 클릭: 점 추가")
    print("- 오른쪽 클릭 또는 u: 마지막 점 취소")
    print("- r: 현재 점 초기화")
    print("- q 또는 ESC: 종료")
    print("권장 클릭 순서: 좌상단 -> 우상단 -> 우하단 -> 좌하단")

    state = ctx.raw_roi_state
    while not state.done:
        annotated = draw_points(frame, state.points, f"raw conveyor_roi: {len(state.points)}/4", (0, 255, 0))
        cv2.imshow(WINDOW_RAW_ROI, scale_for_display(annotated, ctx.display_scale))
        key = cv2.waitKey(20) & 0xFF
        if key in (ord("q"), 27):
            raise SystemExit("Cancelled")
        if key == ord("u"):
            state.undo()
        if key == ord("r"):
            state.reset()

    annotated = draw_points(frame, state.points, "raw conveyor_roi: done", (0, 255, 0))
    cv2.imshow(WINDOW_RAW_ROI, scale_for_display(annotated, ctx.display_scale))
    cv2.waitKey(300)
    cv2.destroyWindow(WINDOW_RAW_ROI)
    return state.points.copy()


def load_existing_runtime_defaults(output_json: Path) -> dict[str, Any]:
    if not output_json.exists():
        return {}
    try:
        with output_json.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    defaults = data.get("runtime_defaults")
    return defaults if isinstance(defaults, dict) else {}


def save_raw_roi_outputs(
    args: argparse.Namespace,
    frame: np.ndarray,
    source_meta: dict[str, Any],
    roi_quad_ordered: np.ndarray,
) -> Path:
    cv2 = import_cv2()
    output_json = Path(args.output).expanduser().resolve()
    output_json.parent.mkdir(parents=True, exist_ok=True)

    preview_dir = output_json.parent / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    stem = output_json.stem
    raw_preview = preview_dir / f"{stem}_raw_roi.png"
    raw_frame_image = preview_dir / f"{stem}_raw_frame.png"

    raw_annotated = draw_points(frame, roi_quad_ordered.astype(int).tolist(), "raw conveyor_roi", (0, 255, 0))
    cv2.imwrite(str(raw_preview), raw_annotated)
    cv2.imwrite(str(raw_frame_image), frame)

    runtime_defaults = load_existing_runtime_defaults(output_json)
    if not runtime_defaults:
        runtime_defaults = {
            "perspective_mode": "raw",
            "cube_colors": ["red", "green"],
            "red_green_same_meaning": True,
            "disappear_stable_frames": 10,
            "motor_direction": "clockwise",
            "websocket": {
                "enabled": True,
                "host": "0.0.0.0",
                "port": 28765,
                "payload": "JSON with detections and image_jpeg_base64",
            },
            "modbus": {"mode": "tcp", "library": "pymodbus==3.13.1"},
        }
    runtime_defaults["perspective_mode"] = "raw"

    result = {
        "schema_version": 2,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "SmartFarmProject conveyor direct raw-frame ROI detection without top-view warping",
        "source": source_meta,
        "raw_frame": {
            "width": int(frame.shape[1]),
            "height": int(frame.shape[0]),
            "channels": int(frame.shape[2]) if frame.ndim == 3 else 1,
        },
        "raw_roi": {
            "coordinate_space": "raw",
            "point_order_mode": args.point_order,
            "quad_xy_tl_tr_br_bl": roi_quad_ordered.astype(int).tolist(),
            "xyxy": roi_xyxy_from_quad(roi_quad_ordered),
        },
        "runtime_defaults": runtime_defaults,
        "preview_files": {
            "raw_roi": str(raw_preview),
            "raw_frame": str(raw_frame_image),
        },
        "notes": [
            "This config intentionally skips perspective/top-view warping.",
            "Use raw_roi.quad_xy_tl_tr_br_bl or raw_roi.xyxy for OpenCV detection in the original D435i color frame.",
            "If the D435i position, resolution, or color stream topic changes, rerun this selector.",
        ],
    }

    with output_json.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return output_json


def self_test(args: argparse.Namespace) -> Path:
    """Non-GUI smoke test for headless verification."""

    frame, source_meta = load_frame_from_args(args)
    h, w = frame.shape[:2]
    roi_quad = np.array(
        [
            [int(w * 0.20), int(h * 0.15)],
            [int(w * 0.80), int(h * 0.15)],
            [int(w * 0.80), int(h * 0.85)],
            [int(w * 0.20), int(h * 0.85)],
        ],
        dtype="float32",
    )
    roi_ordered = order_points_tl_tr_br_bl(roi_quad, args.point_order)
    return save_raw_roi_outputs(args, frame, source_meta, roi_ordered)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OpenCV GUI tool for selecting conveyor ROI directly on the raw D435i frame.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--image", type=Path, default=default_sample_image(), help="Image path to use as the calibration frame")
    source.add_argument("--ros-topic", default=None, help="ROS2 sensor_msgs/Image topic. Press SPACE to freeze one live frame.")
    source.add_argument("--camera", type=int, help="OpenCV camera index. Press SPACE to freeze one frame.")
    source.add_argument("--video", type=Path, help="Video path. Uses the first frame.")
    parser.add_argument("--output", type=Path, default=Path("config/conveyor_roi_raw.json"), help="Output JSON path")
    parser.add_argument("--display-scale", type=float, default=1.0, help="Scale GUI display while saving original raw-frame coordinates")
    parser.add_argument(
        "--point-order",
        choices=["click", "auto"],
        default="click",
        help="How to order 4 clicked points. click trusts TL->TR->BR->BL click order; auto uses coordinate sorting.",
    )
    parser.add_argument("--ros-timeout-sec", type=float, default=10.0, help="Timeout while waiting for the first ROS Image")
    parser.add_argument("--self-test", action="store_true", help="Run a non-interactive smoke test with generated raw ROI points")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.display_scale <= 0:
        raise SystemExit("--display-scale must be positive")

    if args.self_test:
        output_path = self_test(args)
        print(f"Self-test raw ROI JSON saved: {output_path}")
        return 0

    cv2 = import_cv2()
    frame, source_meta = load_frame_from_args(args)
    ctx = RawRoiContext(display_scale=args.display_scale)

    roi_clicked = interactive_collect_raw_roi(frame, ctx)
    roi_quad_ordered = order_points_tl_tr_br_bl(roi_clicked, args.point_order)
    output_path = save_raw_roi_outputs(args, frame, source_meta, roi_quad_ordered)

    print(f"\nSaved raw ROI calibration JSON: {output_path}")
    print("Preview images are in:", output_path.parent / "previews")
    print("raw_roi.quad_xy_tl_tr_br_bl =", roi_quad_ordered.astype(int).tolist())
    print("raw_roi.xyxy =", roi_xyxy_from_quad(roi_quad_ordered))

    final = draw_points(frame, roi_quad_ordered.astype(int).tolist(), "raw conveyor_roi result", (0, 255, 0))
    cv2.imshow("result_raw_roi__press_any_key", scale_for_display(final, ctx.display_scale))
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

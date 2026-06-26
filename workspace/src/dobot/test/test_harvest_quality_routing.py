from __future__ import annotations

import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "dobot"
sys.path.insert(0, str(PACKAGE_DIR.parent))


def test_destination_for_normal_quality_uses_conveyor_pose():
    from dobot.harvest_test import Pose4, destination_for_quality_status

    conveyor = Pose4(1.0, 2.0, 3.0, 0.0)
    defect_box = Pose4(4.0, 5.0, 6.0, 0.0)

    label, pose = destination_for_quality_status("normal", conveyor, defect_box)

    assert label == "conveyor normal place"
    assert pose == conveyor


def test_destination_for_defect_quality_uses_defect_box_pose():
    from dobot.harvest_test import Pose4, destination_for_quality_status

    conveyor = Pose4(1.0, 2.0, 3.0, 0.0)
    defect_box = Pose4(4.0, 5.0, 6.0, 0.0)

    label, pose = destination_for_quality_status("defect", conveyor, defect_box)

    assert label == "defect box place"
    assert pose == defect_box

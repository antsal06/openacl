"""Tests for the pure name/sign-mapping helpers in :mod:`openacl.backends.sports2d`.

These do not invoke Sports2D itself (see ``test_sports2d_slow.py`` for the full engine run,
gated behind ``--runslow``); they check the keypoint/angle name mapping and the small amount of
geometry openacl computes itself (trunk lean sign, visible-side heuristic, walking direction).
"""

from __future__ import annotations

import numpy as np
import pytest

from openacl.backends.sports2d import (
    _JOINT_ANGLE_MAP,
    _KEYPOINT_MAP,
    _resolve_camera_near_side,
    _trunk_lean_from_segment_deg,
    _walking_direction,
)
from openacl.schema import KEYPOINT_NAMES


def test_keypoint_map_targets_are_schema_names() -> None:
    for marker_name, (base_name, side) in _KEYPOINT_MAP.items():
        assert base_name in KEYPOINT_NAMES, f"{marker_name} maps to unknown keypoint {base_name!r}"
        assert side in ("L", "R")
    # Sports2D's own L/R labelling is anatomical (subject's side), so no extra flip needed.
    assert _KEYPOINT_MAP["RKnee"] == ("knee", "R")
    assert _KEYPOINT_MAP["LKnee"] == ("knee", "L")


def test_joint_angle_map_covers_the_clinical_triad() -> None:
    targets = {base_name for base_name, _side in _JOINT_ANGLE_MAP.values()}
    assert targets == {"knee_flexion_deg", "hip_flexion_deg", "ankle_dorsiflexion_deg"}
    assert _JOINT_ANGLE_MAP["right knee"] == ("knee_flexion_deg", "R")
    assert _JOINT_ANGLE_MAP["left hip"] == ("hip_flexion_deg", "L")
    assert _JOINT_ANGLE_MAP["right ankle"] == ("ankle_dorsiflexion_deg", "R")


def test_trunk_lean_upright_is_zero() -> None:
    # Sports2D's raw 'trunk' segment angle for a perfectly vertical trunk is 90 deg
    # (Neck-Hip vector vs. horizontal); openacl's transform maps that to 0 deg lean.
    assert _trunk_lean_from_segment_deg(np.array([90.0]))[0] == pytest.approx(0.0)


def test_trunk_lean_forward_is_positive() -> None:
    # A trunk_deg below 90 (per the module docstring's geometry) should read as forward lean.
    leaned = _trunk_lean_from_segment_deg(np.array([80.0]))[0]
    assert leaned == pytest.approx(10.0)
    assert leaned > 0


def _toe_heel_markers(right_forward: bool, left_forward: bool) -> dict[str, np.ndarray]:
    """Minimal marker set for the visible-side heuristic: only X matters."""
    sign_r = 1.0 if right_forward else -1.0
    sign_l = 1.0 if left_forward else -1.0
    zeros = np.zeros((3, 3))

    def col(x: float) -> np.ndarray:
        arr = zeros.copy()
        arr[:, 0] = x
        return arr

    return {
        "RBigToe": col(sign_r * 10.0),
        "RHeel": col(0.0),
        "LBigToe": col(sign_l * 10.0),
        "LHeel": col(0.0),
    }


def test_resolve_camera_near_side_auto_right() -> None:
    markers = _toe_heel_markers(right_forward=True, left_forward=True)
    assert _resolve_camera_near_side(markers, "auto") == "R"


def test_resolve_camera_near_side_auto_left() -> None:
    markers = _toe_heel_markers(right_forward=False, left_forward=False)
    assert _resolve_camera_near_side(markers, "auto") == "L"


def test_resolve_camera_near_side_explicit_overrides_auto() -> None:
    markers = _toe_heel_markers(right_forward=True, left_forward=True)
    assert _resolve_camera_near_side(markers, "left") == "L"


def test_resolve_camera_near_side_none_for_front_back() -> None:
    markers = _toe_heel_markers(right_forward=True, left_forward=True)
    assert _resolve_camera_near_side(markers, "front") is None
    assert _resolve_camera_near_side(markers, "none") is None


def test_walking_direction_from_hip_x() -> None:
    forward = {"RHip": np.column_stack([np.linspace(0, 10, 5), np.zeros(5), np.zeros(5)])}
    assert _walking_direction(forward) == "+x"
    backward = {"LHip": np.column_stack([np.linspace(10, 0, 5), np.zeros(5), np.zeros(5)])}
    assert _walking_direction(backward) == "-x"


def test_walking_direction_unknown_without_hips() -> None:
    assert _walking_direction({}) == "unknown"

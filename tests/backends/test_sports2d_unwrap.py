"""Tests for :func:`openacl.backends.sports2d.unwrap_angles` (ADR-0010).

Sports2D decides the visible side per frame from foot orientation and mirrors the x
coordinates before computing joint-angle sign. When that per-frame decision is wrong (a
heel/toe swap on a partly occluded foot, typically the camera-far side) the affected channel
comes out shifted by a clean +-180 deg -- the range of motion is preserved, only the offset is
wrong. ``unwrap_angles`` detects samples outside the channel's plausible window
(:data:`WRAP_RULES_DEG`) and shifts them back by 180 deg in place.
"""

from __future__ import annotations

import numpy as np
import pytest

from openacl.backends.sports2d import WRAP_RULES_DEG, unwrap_angles


def test_knee_channel_shifted_by_minus_180_is_restored() -> None:
    true_knee = np.array([-10.0, 0.0, 20.0, 45.0, 63.0, 30.0])
    wrapped = true_knee - 180.0  # e.g. -190, -180, -160, -135, -117, -150
    angles = {"knee_flexion_deg_L": wrapped.copy()}

    shifted = unwrap_angles(angles)

    assert shifted == {"knee_flexion_deg_L": true_knee.size}
    np.testing.assert_allclose(angles["knee_flexion_deg_L"], true_knee)


def test_knee_channel_range_of_motion_is_preserved_after_unwrap() -> None:
    true_knee = np.array([-5.0, 10.0, 35.0, 63.0, 40.0, 5.0])
    true_rom = np.nanmax(true_knee) - np.nanmin(true_knee)
    wrapped = true_knee - 180.0
    angles = {"knee_flexion_deg_R": wrapped.copy()}

    unwrap_angles(angles)

    unwrapped_rom = np.nanmax(angles["knee_flexion_deg_R"]) - np.nanmin(
        angles["knee_flexion_deg_R"]
    )
    assert unwrapped_rom == pytest.approx(true_rom)


def test_ankle_channel_shifted_by_plus_180_is_restored() -> None:
    true_ankle = np.array([-15.0, -5.0, 0.0, 10.0, 20.0])
    wrapped = true_ankle + 180.0  # e.g. 165, 175, 180, 190, 200
    angles = {"ankle_dorsiflexion_deg_L": wrapped.copy()}

    shifted = unwrap_angles(angles)

    assert shifted == {"ankle_dorsiflexion_deg_L": true_ankle.size}
    np.testing.assert_allclose(angles["ankle_dorsiflexion_deg_L"], true_ankle)


def test_values_already_inside_the_plausible_window_are_untouched() -> None:
    plausible = np.array([-10.0, 0.0, 30.0, 60.0, 90.0])
    angles = {"knee_flexion_deg_L": plausible.copy()}

    shifted = unwrap_angles(angles)

    assert shifted == {}
    np.testing.assert_allclose(angles["knee_flexion_deg_L"], plausible)


def test_channel_without_a_wrap_rule_is_untouched() -> None:
    hip = np.array([-200.0, -190.0, 400.0, 0.0])  # absurd values, but hip has no rule
    angles = {"hip_flexion_deg_L": hip.copy()}

    shifted = unwrap_angles(angles)

    assert shifted == {}
    np.testing.assert_allclose(angles["hip_flexion_deg_L"], hip)


def test_nan_stays_nan() -> None:
    wrapped = np.array([-190.0, np.nan, -160.0, np.nan])
    angles = {"knee_flexion_deg_R": wrapped.copy()}

    shifted = unwrap_angles(angles)

    assert shifted == {"knee_flexion_deg_R": 2}
    result = angles["knee_flexion_deg_R"]
    assert np.isnan(result[1])
    assert np.isnan(result[3])
    np.testing.assert_allclose(result[[0, 2]], [-10.0, 20.0])


def test_wrap_rules_cover_knee_and_ankle_only() -> None:
    assert set(WRAP_RULES_DEG) == {"knee_flexion_deg", "ankle_dorsiflexion_deg"}

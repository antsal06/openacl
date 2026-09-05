"""Tests for the symmetry measures (Robinson SI, Plotnik GA, curve RMS)."""

from __future__ import annotations

import numpy as np
import pytest

from openacl.core.pipeline import analyze
from openacl.core.symmetry import (
    curve_rms_difference_deg,
    gait_asymmetry_pct,
    symmetry_index_pct,
)
from tests.core.synthetic import make_synthetic_gait


def test_symmetry_index_formula():
    """SI = (X_R - X_L) / (0.5 * (|X_R| + |X_L|)) * 100, positive when right is larger."""
    assert symmetry_index_pct(10.0, 10.0) == pytest.approx(0.0)
    assert symmetry_index_pct(10.0, 11.0) == pytest.approx(0.1 / 1.05 * 100.0)
    assert symmetry_index_pct(11.0, 10.0) == pytest.approx(-0.1 / 1.05 * 100.0)
    assert np.isnan(symmetry_index_pct(0.0, 0.0))
    assert np.isnan(symmetry_index_pct(np.nan, 1.0))


def test_gait_asymmetry_formula():
    assert gait_asymmetry_pct(0.44, 0.44) == pytest.approx(0.0)
    assert gait_asymmetry_pct(0.4, 0.44) == pytest.approx(100.0 * abs(np.log(1.1)))
    assert gait_asymmetry_pct(0.44, 0.4) == pytest.approx(100.0 * abs(np.log(1.1)))
    assert np.isnan(gait_asymmetry_pct(0.0, 0.4))


def test_curve_rms_difference():
    a = np.zeros(101)
    b = np.full(101, 3.0)
    assert curve_rms_difference_deg(a, a) == pytest.approx(0.0)
    assert curve_rms_difference_deg(a, b) == pytest.approx(3.0)
    b[0] = np.nan
    assert curve_rms_difference_deg(a, b) == pytest.approx(3.0)
    with pytest.raises(ValueError):
        curve_rms_difference_deg(a, np.zeros(50))


def test_symmetric_gait_gives_si_near_zero():
    result, _ = make_synthetic_gait(unit="m")
    symmetry = analyze(result).symmetry
    for name, value in symmetry.symmetry_index_pct.items():
        assert abs(value) < 1.0, f"{name} = {value}"
    assert symmetry.gait_asymmetry_pct < 1.0
    for name, rms in symmetry.curve_rms_diff_deg.items():
        assert rms < 0.5, f"{name} = {rms}"


def test_ten_percent_higher_right_knee_peak_gives_the_expected_si():
    """peak_R / peak_L = 1.1  ->  SI = (1.1 - 1) / (0.5 * 2.1) * 100 = 9.52 %."""
    expected_si = 0.1 / 1.05 * 100.0
    result, truth = make_synthetic_gait(peak_knee_swing_deg_R=66.0)
    assert truth.peak_knee_swing_deg["R"] / truth.peak_knee_swing_deg["L"] == pytest.approx(1.1)
    si = analyze(result).symmetry.symmetry_index_pct
    assert si["peak_knee_flexion_swing_deg"] == pytest.approx(expected_si, abs=1.0)


def test_ten_percent_longer_right_swing_shows_up_in_si_and_ga():
    """swing_R / swing_L = 1.1 -> SI ~ 9.5 %, GA ~ 9.5 %.

    Event detection quantises to whole frames and the 6 Hz filter biases the toe-off by up to
    one frame, which is ~1.5 % of the stride, so the tolerance here is wider than the formula
    test above.
    """
    # left stance 60 % -> swing 40 %; right swing 44 % -> right stance 56 %
    result, truth = make_synthetic_gait(unit="m", stance_pct_R=56.0)
    assert truth.swing_time_s["R"] / truth.swing_time_s["L"] == pytest.approx(1.1)
    expected_si = 0.1 / 1.05 * 100.0

    analysis = analyze(result)
    si = analysis.symmetry.symmetry_index_pct
    assert si["swing_time_s"] == pytest.approx(expected_si, abs=3.0)
    assert si["swing_pct"] == pytest.approx(expected_si, abs=3.0)
    assert si["stance_pct"] < 0  # the right side has the shorter stance
    assert si["stride_time_s"] == pytest.approx(0.0, abs=0.5)
    assert analysis.symmetry.gait_asymmetry_pct == pytest.approx(100.0 * abs(np.log(1.1)), abs=3.0)


def test_operated_side_flips_the_sign_for_a_left_reconstruction():
    result, _ = make_synthetic_gait(unit="m", stance_pct_R=56.0)
    analysis = analyze(result, operated_side="L")
    si = analysis.symmetry.symmetry_index_pct
    si_op = analysis.symmetry.symmetry_index_operated_pct
    assert si_op is not None
    for name in si:
        assert si_op[name] == pytest.approx(-si[name])
    # operated left, longer right swing -> the operated limb has the shorter swing
    assert si_op["swing_time_s"] < 0
    assert any("contralateral limb" in w for w in analysis.symmetry.warnings)


def test_operated_right_keeps_the_sign():
    result, _ = make_synthetic_gait(unit="m", stance_pct_R=56.0)
    analysis = analyze(result, operated_side="R")
    si = analysis.symmetry.symmetry_index_pct
    si_op = analysis.symmetry.symmetry_index_operated_pct
    assert si_op["swing_time_s"] == pytest.approx(si["swing_time_s"])


def test_curve_symmetry_detects_a_knee_flexion_difference():
    """10 deg less peak swing flexion on the right must show up as a curve RMS difference."""
    result, _ = make_synthetic_gait(peak_knee_swing_deg_R=50.0)
    analysis = analyze(result)
    assert analysis.symmetry.curve_rms_diff_deg["knee_flexion_deg"] > 2.0
    assert analysis.symmetry.curve_rms_diff_deg["hip_flexion_deg"] < 0.5
    si = analysis.symmetry.symmetry_index_pct["peak_knee_flexion_swing_deg"]
    assert si == pytest.approx(symmetry_index_pct(60.0, 50.0), abs=1.0)

"""Tests for cycle segmentation and time normalisation."""

from __future__ import annotations

import numpy as np
import pytest

from openacl.core.cycles import normalize_cycles
from openacl.core.events import detect_events
from openacl.core.pipeline import filter_result
from tests.core.synthetic import make_synthetic_gait


def _cycles(**overrides):
    result, truth = make_synthetic_gait(**overrides)
    filtered = filter_result(result)
    events = detect_events(filtered, smooth=False)
    return normalize_cycles(filtered, events), truth


def test_curves_have_101_points_per_cycle():
    cycles, truth = _cycles()
    assert cycles.n_points == 101
    assert np.allclose(cycles.phase_pct, np.linspace(0, 100, 101))
    for side in ("L", "R"):
        arr = cycles.cycle_array("knee_flexion_deg", side, only_valid=False)
        assert arr.ndim == 2
        assert arr.shape[1] == 101
        assert arr.shape[0] == truth.heel_strikes[side].size - 1


def test_sideless_channel_is_available_for_both_sides():
    cycles, _ = _cycles()
    assert "trunk_lean_deg" in cycles.channels("L")
    assert "trunk_lean_deg" in cycles.channels("R")
    assert "knee_flexion_deg" in cycles.channels("L")


def test_mean_curve_reproduces_the_generator_curve():
    cycles, truth = _cycles()
    for side in ("L", "R"):
        mean_curve = cycles.mean_curve_deg("knee_flexion_deg", side)
        assert np.max(np.abs(mean_curve - truth.knee_curve_deg[side])) < 1.5


def test_peak_values_match_the_generator():
    cycles, truth = _cycles()
    for side in ("L", "R"):
        curve = cycles.mean_curve_deg("knee_flexion_deg", side)
        assert np.max(curve) == pytest.approx(truth.peak_knee_swing_deg[side], abs=1.0)
        assert np.max(curve[:30]) == pytest.approx(truth.peak_knee_stance_deg[side], abs=1.0)


def test_all_cycles_valid_for_a_clean_signal():
    cycles, _ = _cycles()
    for side in ("L", "R"):
        assert cycles.n_valid(side) == len(cycles.meta[side])
        assert all(m.reason == "" for m in cycles.meta[side])


def test_cycle_metadata_carries_start_time_and_duration():
    cycles, truth = _cycles()
    meta = cycles.meta["L"]
    assert all(m.duration_s == pytest.approx(truth.stride_time_s, abs=0.05) for m in meta)
    starts = [m.start_time_s for m in meta]
    assert starts == sorted(starts)
    assert meta[0].side == "L"
    assert meta[0].index == 0


def test_long_gap_marks_the_cycle_invalid():
    """A 0.5 s dropout leaves more than 20 % NaN in one cycle, which must be flagged."""
    cycles, _ = _cycles(nan_gaps_s=((5.0, 5.5),), nan_channels=("knee_flexion_deg_L",))
    invalid = [m for m in cycles.meta["L"] if not m.valid]
    assert invalid, "expected at least one invalid cycle"
    assert any("missing samples" in m.reason for m in invalid)
    assert cycles.n_valid("L") < len(cycles.meta["L"])


def test_outlier_duration_is_flagged():
    """A missed heel strike doubles one stride; the duration rule must catch it."""
    result, _ = make_synthetic_gait()
    filtered = filter_result(result)
    events = detect_events(filtered, smooth=False)
    trimmed = np.delete(events.heel_strikes_L, 4)
    events = type(events)(
        **{
            **events.__dict__,
            "heel_strikes_L": trimmed,
            "heel_strike_times_L_s": filtered.time_s[trimmed],
        }
    )
    cycles = normalize_cycles(filtered, events)
    assert any("deviates" in m.reason for m in cycles.meta["L"])

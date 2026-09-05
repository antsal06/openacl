"""Tests for gait event detection (Zeni et al. 2008) on the synthetic walker."""

from __future__ import annotations

from itertools import pairwise

import numpy as np
import pytest

from openacl.core.events import detect_events, estimate_direction_sign
from openacl.core.pipeline import filter_result
from tests.core.synthetic import make_synthetic_gait

TOLERANCE_FRAMES = 2


def _match(detected: np.ndarray, truth: np.ndarray) -> np.ndarray:
    """Signed frame error of every truth event against its nearest detected event."""
    assert detected.size, "no events detected"
    return np.array([detected[np.argmin(np.abs(detected - f))] - f for f in truth])


@pytest.mark.parametrize("side", ["L", "R"])
def test_heel_strikes_within_two_frames(side):
    result, truth = make_synthetic_gait()
    events = detect_events(filter_result(result), smooth=False)
    detected = events.heel_strikes(side)
    assert detected.size == truth.heel_strikes[side].size
    errors = _match(detected, truth.heel_strikes[side])
    assert np.abs(errors).max() <= TOLERANCE_FRAMES


@pytest.mark.parametrize("side", ["L", "R"])
def test_toe_offs_within_two_frames(side):
    result, truth = make_synthetic_gait()
    events = detect_events(filter_result(result), smooth=False)
    errors = _match(events.toe_offs(side), truth.toe_offs[side])
    assert np.abs(errors).max() <= TOLERANCE_FRAMES


def test_event_times_match_frame_indices():
    result, _ = make_synthetic_gait()
    events = detect_events(result)
    assert np.allclose(events.heel_strike_times_L_s, result.time_s[events.heel_strikes_L])
    assert np.allclose(events.toe_off_times_R_s, result.time_s[events.toe_offs_R])


def test_direction_is_estimated_when_backend_does_not_report_it():
    result, truth = make_synthetic_gait(declare_direction=False)
    sign, source = estimate_direction_sign(result)
    assert sign == 1
    assert source == "estimated_from_hip_displacement"
    events = detect_events(filter_result(result), smooth=False)
    errors = _match(events.heel_strikes_L, truth.heel_strikes["L"])
    assert np.abs(errors).max() <= TOLERANCE_FRAMES


def test_walking_in_negative_x_gives_the_same_events():
    forward, truth = make_synthetic_gait()
    backward, _ = make_synthetic_gait(direction="-x", declare_direction=False)
    events_f = detect_events(filter_result(forward), smooth=False)
    events_b = detect_events(filter_result(backward), smooth=False)
    assert events_b.direction_sign == -1
    assert np.array_equal(events_f.heel_strikes_L, events_b.heel_strikes_L)
    assert np.abs(_match(events_b.heel_strikes_R, truth.heel_strikes["R"])).max() <= 2


def test_sides_alternate():
    result, _ = make_synthetic_gait()
    events = detect_events(filter_result(result), smooth=False)
    merged = sorted(
        [(int(f), "L") for f in events.heel_strikes_L]
        + [(int(f), "R") for f in events.heel_strikes_R]
    )
    sides = [s for _, s in merged]
    assert all(a != b for a, b in pairwise(sides))


def test_step_times_are_plausible():
    result, _ = make_synthetic_gait()
    events = detect_events(filter_result(result), smooth=False)
    merged = np.sort(np.concatenate([events.heel_strikes_L, events.heel_strikes_R]))
    step_times_s = np.diff(merged) / result.fps
    assert step_times_s.min() >= 0.3
    assert step_times_s.max() <= 2.0


def test_short_nan_gaps_do_not_break_detection():
    """Gaps below 0.25 s are interpolated; events outside the gap stay exact."""
    result, truth = make_synthetic_gait(nan_gaps_s=((3.0, 3.15), (7.4, 7.55)))
    events = detect_events(filter_result(result), smooth=False)
    assert events.heel_strikes_L.size == truth.heel_strikes["L"].size
    errors = _match(events.heel_strikes_L, truth.heel_strikes["L"])
    assert np.abs(errors).max() <= TOLERANCE_FRAMES


def test_long_nan_gap_degrades_gracefully():
    """A 0.6 s dropout may cost events, but must not crash or invent extra ones."""
    result, truth = make_synthetic_gait(nan_gaps_s=((5.0, 5.6),))
    events = detect_events(filter_result(result), smooth=False)
    assert events.heel_strikes_L.size <= truth.heel_strikes["L"].size
    assert events.heel_strikes_L.size >= truth.heel_strikes["L"].size - 2


def test_noise_does_not_create_extra_events():
    result, truth = make_synthetic_gait(noise_px=3.0, noise_deg=1.0, seed=3)
    events = detect_events(filter_result(result), smooth=False)
    assert events.heel_strikes_L.size == truth.heel_strikes["L"].size
    errors = _match(events.heel_strikes_L, truth.heel_strikes["L"])
    assert np.abs(errors).max() <= TOLERANCE_FRAMES


def test_missing_keypoint_raises():
    result, _ = make_synthetic_gait()
    del result.keypoints["heel_L"]
    with pytest.raises(ValueError, match="heel_L"):
        detect_events(result)

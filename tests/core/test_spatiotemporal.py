"""Tests for the spatio-temporal parameters."""

from __future__ import annotations

import numpy as np
import pytest

from openacl.core.cycles import normalize_cycles
from openacl.core.events import detect_events
from openacl.core.pipeline import filter_result
from openacl.core.spatiotemporal import ParamStat, compute_spatiotemporal
from tests.core.synthetic import make_synthetic_gait

STANCE_TOLERANCE_PCT = 2.0


def _params(**overrides):
    result, truth = make_synthetic_gait(**overrides)
    filtered = filter_result(result)
    events = detect_events(filtered, smooth=False)
    cycles = normalize_cycles(filtered, events)
    masks = {s: cycles.valid_mask(s) for s in ("L", "R")}
    return compute_spatiotemporal(filtered, events, valid_masks=masks), truth


def test_param_stat_from_values():
    stat = ParamStat.from_values([1.0, 2.0, 3.0, np.nan])
    assert stat.mean == pytest.approx(2.0)
    assert stat.sd == pytest.approx(1.0)
    assert stat.n == 3
    empty = ParamStat.from_values([np.nan, np.nan])
    assert empty.n == 0
    assert np.isnan(empty.mean)


@pytest.mark.parametrize("side", ["L", "R"])
def test_stride_and_step_time(side):
    st, truth = _params()
    assert st.side(side).stride_time_s.mean == pytest.approx(truth.stride_time_s, abs=0.02)
    assert st.side(side).step_time_s.mean == pytest.approx(truth.step_time_s[side], abs=0.03)
    assert st.side(side).stride_time_s.n >= 10


@pytest.mark.parametrize("side", ["L", "R"])
def test_stance_and_swing_within_two_percent(side):
    st, truth = _params()
    assert st.side(side).stance_pct.mean == pytest.approx(
        truth.stance_pct[side], abs=STANCE_TOLERANCE_PCT
    )
    assert st.side(side).swing_pct.mean == pytest.approx(
        truth.swing_pct[side], abs=STANCE_TOLERANCE_PCT
    )
    assert st.side(side).stance_pct.mean + st.side(side).swing_pct.mean == pytest.approx(100.0)


def test_double_support_and_cadence():
    st, truth = _params()
    assert st.both.double_support_pct.mean == pytest.approx(truth.double_support_pct, abs=2.0)
    assert st.both.cadence_steps_per_min.mean == pytest.approx(truth.cadence_steps_per_min, abs=2.0)


def test_asymmetric_stance_is_measured_per_side():
    st, truth = _params(stance_pct_R=56.0)
    assert st.L.stance_pct.mean == pytest.approx(60.0, abs=STANCE_TOLERANCE_PCT)
    assert st.R.stance_pct.mean == pytest.approx(56.0, abs=STANCE_TOLERANCE_PCT)
    assert truth.stance_pct["R"] == 56.0


def test_spatial_parameters_are_none_for_pixel_keypoints():
    st, _ = _params(unit="px")
    assert st.keypoint_unit == "px"
    assert st.both.step_length_m is None
    assert st.both.stride_length_m is None
    assert st.both.walking_speed_m_s is None
    assert any("keypoint_unit" in w for w in st.warnings)


def test_spatial_parameters_for_metric_keypoints():
    st, truth = _params(unit="m")
    assert st.both.walking_speed_m_s.mean == pytest.approx(truth.walking_speed_m_s, abs=0.05)
    assert st.both.stride_length_m.mean == pytest.approx(truth.stride_length_m, abs=0.05)
    for side in ("L", "R"):
        assert st.side(side).step_length_m.mean == pytest.approx(
            truth.step_length_m[side], abs=0.05
        )


def test_values_are_plausible_against_healthy_reference_ranges():
    """Healthy adults: stance ~60 %, double support ~20-24 %, cadence 100-120 steps/min."""
    st, _ = _params(unit="m")
    assert 55.0 <= st.both.stance_pct.mean <= 65.0
    assert 15.0 <= st.both.double_support_pct.mean <= 26.0
    assert 100.0 <= st.both.cadence_steps_per_min.mean <= 120.0
    assert 1.0 <= st.both.walking_speed_m_s.mean <= 1.6

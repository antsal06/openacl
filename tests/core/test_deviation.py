"""Tests for GVS / GPS and the norm band container."""

from __future__ import annotations

import numpy as np
import pytest

from openacl.core.deviation import (
    compute_deviation,
    gait_profile_score_deg,
    gait_variable_score_deg,
    pct_outside_2sd,
)
from openacl.core.normband import NormBand
from openacl.core.pipeline import analyze
from tests.core.synthetic import make_synthetic_gait

SOURCE = "test fixture"


def _flat_band(mean_deg: float = 0.0, sd_deg: float = 1.0, n: int = 20) -> NormBand:
    return NormBand(mean=np.full(101, mean_deg), sd=np.full(101, sd_deg), n=n, source=SOURCE)


def test_normband_validates_shapes_and_n():
    with pytest.raises(ValueError):
        NormBand(mean=np.zeros(101), sd=np.zeros(50), n=10, source=SOURCE)
    with pytest.raises(ValueError):
        NormBand(mean=np.zeros(101), sd=-np.ones(101), n=10, source=SOURCE)
    with pytest.raises(ValueError):
        NormBand(mean=np.zeros(101), sd=np.ones(101), n=0, source=SOURCE)


def test_normband_from_curves_and_z_scores():
    curves = np.array([np.full(101, 10.0), np.full(101, 12.0), np.full(101, 14.0)])
    band = NormBand.from_curves(curves, source=SOURCE)
    assert band.n == 3
    assert band.mean == pytest.approx(np.full(101, 12.0))
    assert band.sd == pytest.approx(np.full(101, 2.0))
    assert band.z_scores(np.full(101, 14.0)) == pytest.approx(np.ones(101))
    assert band.upper_2sd == pytest.approx(np.full(101, 16.0))
    assert band.lower_2sd == pytest.approx(np.full(101, 8.0))


def test_gvs_is_zero_against_the_own_mean_curve():
    band = NormBand(mean=np.linspace(0, 60, 101), sd=np.full(101, 5.0), n=10, source=SOURCE)
    assert gait_variable_score_deg(band.mean.copy(), band) == pytest.approx(0.0)


def test_gvs_is_the_rms_distance():
    band = _flat_band()
    assert gait_variable_score_deg(np.full(101, 3.0), band) == pytest.approx(3.0)
    curve = np.zeros(101)
    curve[:50] = 4.0
    curve[50:] = 0.0
    expected = np.sqrt(50 / 101 * 16.0)
    assert gait_variable_score_deg(curve, band) == pytest.approx(expected)


def test_gps_is_the_rms_over_the_gvs():
    assert gait_profile_score_deg({"a": 3.0, "b": 4.0}) == pytest.approx(np.sqrt(12.5))
    assert gait_profile_score_deg({"a": 3.0, "b": float("nan")}) == pytest.approx(3.0)
    assert np.isnan(gait_profile_score_deg({}))


def test_pct_outside_2sd():
    band = _flat_band(mean_deg=0.0, sd_deg=1.0)
    assert pct_outside_2sd(np.zeros(101), band) == pytest.approx(0.0)
    assert pct_outside_2sd(np.full(101, 3.0), band) == pytest.approx(100.0)
    curve = np.zeros(101)
    curve[:20] = 5.0
    assert pct_outside_2sd(curve, band) == pytest.approx(20 / 101 * 100.0)


def test_deviation_against_the_own_mean_curve_is_zero():
    """GVS = 0 and GPS = 0 when the norm band is built from the analysed curves themselves."""
    result, _ = make_synthetic_gait()
    analysis = analyze(result)
    bands = {}
    for side in ("L", "R"):
        for channel in analysis.cycles.channels(side):
            curve = analysis.cycles.mean_curve_deg(channel, side)
            bands[f"{channel}_{side}"] = NormBand(
                mean=curve, sd=np.full(101, 3.0), n=1, source=SOURCE
            )
    deviation = compute_deviation(analysis.cycles, bands)
    for side in ("L", "R"):
        assert deviation.gvs_deg[side]
        for channel, gvs in deviation.gvs_deg[side].items():
            assert gvs == pytest.approx(0.0, abs=1e-9), channel
            assert deviation.pct_outside_2sd[side][channel] == pytest.approx(0.0)
        assert deviation.gps_deg[side] == pytest.approx(0.0, abs=1e-9)
    assert deviation.missing_bands == ()
    assert all(source == SOURCE for source in deviation.band_sources.values())


def test_deviation_detects_a_shifted_curve():
    result, _ = make_synthetic_gait()
    analysis = analyze(result)
    curve = analysis.cycles.mean_curve_deg("knee_flexion_deg", "L")
    band = NormBand(mean=curve - 5.0, sd=np.full(101, 1.0), n=25, source=SOURCE)
    deviation = compute_deviation(analysis.cycles, {"knee_flexion_deg": band})
    assert deviation.gvs_deg["L"]["knee_flexion_deg"] == pytest.approx(5.0, abs=1e-9)
    assert deviation.pct_outside_2sd["L"]["knee_flexion_deg"] == pytest.approx(100.0)
    assert "hip_flexion_deg" in deviation.missing_bands


def test_no_norm_bands_yields_a_warning_and_no_scores():
    result, _ = make_synthetic_gait()
    analysis = analyze(result, normbands=None)
    assert analysis.deviation.gvs_deg["L"] == {}
    assert any("no norm bands" in w for w in analysis.warnings)


def test_side_specific_band_wins_over_the_generic_one():
    result, _ = make_synthetic_gait()
    analysis = analyze(result)
    curve_l = analysis.cycles.mean_curve_deg("knee_flexion_deg", "L")
    bands = {
        "knee_flexion_deg": NormBand(
            mean=curve_l - 10.0, sd=np.full(101, 1.0), n=25, source="generic"
        ),
        "knee_flexion_deg_L": NormBand(
            mean=curve_l, sd=np.full(101, 1.0), n=25, source="left specific"
        ),
    }
    deviation = compute_deviation(analysis.cycles, bands)
    assert deviation.gvs_deg["L"]["knee_flexion_deg"] == pytest.approx(0.0, abs=1e-9)
    assert deviation.gvs_deg["R"]["knee_flexion_deg"] == pytest.approx(10.0, abs=0.5)


def test_speed_class_keys_from_the_norm_package_are_found():
    """``openacl.norm.load_normbands`` keys look like ``"knee_flexion_deg@comfortable"``."""
    result, _ = make_synthetic_gait()
    analysis = analyze(result)
    curve = analysis.cycles.mean_curve_deg("knee_flexion_deg", "L")
    bands = {
        "knee_flexion_deg@comfortable": NormBand(
            mean=curve, sd=np.full(101, 1.0), n=25, source=SOURCE
        ),
        "knee_flexion_deg@slow": NormBand(
            mean=curve - 20.0, sd=np.full(101, 1.0), n=25, source=SOURCE
        ),
    }
    deviation = compute_deviation(analysis.cycles, bands, speed_class="comfortable")
    assert deviation.gvs_deg["L"]["knee_flexion_deg"] == pytest.approx(0.0, abs=1e-9)
    slow = compute_deviation(analysis.cycles, bands, speed_class="slow")
    assert slow.gvs_deg["L"]["knee_flexion_deg"] == pytest.approx(20.0, abs=1e-9)
    assert compute_deviation(analysis.cycles, bands).missing_bands == (
        "hip_flexion_deg",
        "knee_flexion_deg",
        "trunk_lean_deg",
    )


def test_scalar_norm_band_is_skipped_with_a_warning():
    """The norm package also ships length-1 bands for spatio-temporal parameters."""
    result, _ = make_synthetic_gait()
    analysis = analyze(result)
    bands = {
        "knee_flexion_deg": NormBand(mean=np.array([60.0]), sd=np.array([5.0]), n=25, source=SOURCE)
    }
    deviation = compute_deviation(analysis.cycles, bands)
    assert deviation.gvs_deg["L"] == {}
    assert any("points" in w for w in deviation.warnings)

"""Pooling, symmetry sign, MDC flag logic and JSON serialisation of a whole session."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from openacl.core.events import SIDES
from openacl.session.aggregate import (
    METRICS_BY_NAME,
    Estimate,
    MdcEntry,
    aggregate_session,
    load_subject_mdc,
    pool_cycles,
    resolve_mdc,
    symmetry_index_operated_pct,
)
from openacl.session.model import load_session
from openacl.session.process import process_session
from tests.session.conftest import (
    PEAK_KNEE_SWING_L_DEG,
    PEAK_KNEE_SWING_R_DEG,
    FakeSession,
    build_fake_session,
)


@pytest.fixture
def processed(fake_session: FakeSession, normbands: dict):
    session = load_session(fake_session.root)
    results = process_session(session, normbands=normbands)
    return session, results


def test_every_pass_is_processed_from_the_cache(processed) -> None:
    _session, results = processed
    assert len(results) == 6
    assert all(r.cached for r in results)
    assert all(r.ok for r in results)
    assert all(r.analysis is not None for r in results)


def test_pooled_cycle_count_is_the_sum_over_passes(processed, fake_session: FakeSession) -> None:
    _session, results = processed
    pooled, _warnings = pool_cycles(results, "camera_near")

    expected = {"L": 0, "R": 0}
    for outcome in results:
        near = outcome.camera_near_side
        assert near == fake_session.near_side_of_pass[outcome.name]
        expected[near] += outcome.analysis.cycles.n_valid(near)

    for side in SIDES:
        assert pooled.n_cycles(side) == expected[side] > 0
        assert pooled.curves[side]["knee_flexion_deg"].shape == (expected[side], 101)
        assert pooled.values[side]["stance_pct"].size == expected[side]
    # camera-near pooling takes exactly one side per pass
    assert sorted(set(pooled.pass_of_cycle["R"])) == ["A_pass01", "A_pass03", "A_pass05"]
    assert sorted(set(pooled.pass_of_cycle["L"])) == ["A_pass02", "A_pass04", "A_pass06"]


def test_all_sides_pooling_yields_more_cycles(processed) -> None:
    _session, results = processed
    near, _ = pool_cycles(results, "camera_near")
    both, _ = pool_cycles(results, "all_sides")
    for side in SIDES:
        assert both.n_cycles(side) > near.n_cycles(side)
    assert both.n_cycles("L") + both.n_cycles("R") == 2 * (near.n_cycles("L") + near.n_cycles("R"))


def test_symmetry_index_sign_is_positive_when_operated_is_larger() -> None:
    assert symmetry_index_operated_pct(60.0, 50.0) > 0
    assert symmetry_index_operated_pct(50.0, 60.0) < 0
    assert symmetry_index_operated_pct(50.0, 50.0) == pytest.approx(0.0)
    assert math.isnan(symmetry_index_operated_pct(float("nan"), 50.0))


def test_known_asymmetry_comes_out_with_the_right_sign(processed, normbands: dict) -> None:
    session, results = processed
    summary = aggregate_session(session, results, normbands=normbands)

    entry = summary.symmetry["peak_knee_flexion_swing_deg"]
    # the synthetic right (operated) knee flexes 15 deg less in swing than the left
    assert entry.operated.mean == pytest.approx(PEAK_KNEE_SWING_R_DEG, abs=2.0)
    assert entry.contralateral.mean == pytest.approx(PEAK_KNEE_SWING_L_DEG, abs=2.0)
    assert entry.delta < 0
    assert entry.si_operated_pct < 0
    assert entry.operated_side_known is True


def test_flag_is_only_raised_above_the_mdc(processed, normbands: dict) -> None:
    session, results = processed
    summary = aggregate_session(session, results, normbands=normbands)

    swing = summary.symmetry["peak_knee_flexion_swing_deg"]
    assert swing.mdc is not None
    assert abs(swing.delta) > swing.mdc.value
    assert swing.above_mdc is True

    loading = summary.symmetry["peak_knee_flexion_loading_deg"]
    assert abs(loading.delta) < loading.mdc.value
    assert loading.above_mdc is False


def test_own_mdc_beats_the_literature_value(processed, normbands: dict) -> None:
    session, results = processed
    own = {
        "peak_knee_flexion_swing_deg": MdcEntry(
            value=99.0, unit="deg", source="eigene Wiederholungsmessung", origin="own"
        )
    }
    summary = aggregate_session(session, results, normbands=normbands, subject_mdc=own)
    entry = summary.symmetry["peak_knee_flexion_swing_deg"]
    assert entry.mdc.origin == "own"
    assert entry.mdc.value == 99.0
    assert entry.above_mdc is False


def test_resolve_mdc_falls_back_to_literature_and_to_none() -> None:
    spec = METRICS_BY_NAME["peak_knee_flexion_swing_deg"]
    entry = resolve_mdc(spec, {})
    assert entry is not None and entry.origin == "literature" and entry.value == pytest.approx(9.2)
    assert resolve_mdc(METRICS_BY_NAME["cadence_steps_per_min"], {}) is None


def test_estimate_confidence_interval_brackets_the_mean() -> None:
    estimate = Estimate.from_values([10.0, 12.0, 11.0, 13.0, 9.0], "°")
    assert estimate.n == 5
    assert estimate.ci95_low < estimate.mean < estimate.ci95_high
    assert Estimate.from_values([], "°").n == 0
    assert math.isnan(Estimate.from_values([], "°").mean)


def test_speed_class_comes_from_froude(processed, normbands: dict) -> None:
    session, results = processed
    summary = aggregate_session(session, results, normbands=normbands)
    assert summary.speed_class in ("slow", "comfortable", "fast")
    assert "Froude" in summary.speed_class_source
    speed = summary.metrics["walking_speed_m_s"]["R"].mean
    assert speed == pytest.approx(1.30, abs=0.15)


def test_speed_class_falls_back_without_a_metric_scale(tmp_path: Path, normbands: dict) -> None:
    root = tmp_path / "data" / "sessions" / "no-height"
    build_fake_session(root)
    text = (root / "meta.yaml").read_text(encoding="utf-8")
    (root / "meta.yaml").write_text(text.replace("height_m: 1.8", "height_m: null"), "utf-8")
    session = load_session(root)
    results = process_session(session, normbands=normbands)
    summary = aggregate_session(session, results, normbands=normbands)
    assert summary.speed_class == "comfortable"
    assert "Annahme" in summary.speed_class_source


def test_deviation_scores_are_computed(processed, normbands: dict) -> None:
    session, results = processed
    summary = aggregate_session(session, results, normbands=normbands)
    for side in SIDES:
        assert "knee_flexion_deg" in summary.gvs_deg[side]
        assert math.isfinite(summary.gps_deg[side])
    assert summary.band_sources
    assert "Fukuchi" in " ".join(summary.band_sources.values())
    assert set(summary.norm_curves) >= {"knee_flexion_deg", "hip_flexion_deg"}


def test_per_pass_metrics_exist_for_the_mdc_design(processed, normbands: dict) -> None:
    session, results = processed
    summary = aggregate_session(session, results, normbands=normbands)
    assert len(summary.per_pass) == 6
    for entry in summary.per_pass:
        assert entry["error"] is None
        near = entry["camera_near_side"]
        assert entry["metrics"][near]["stance_pct"] > 0
        assert entry["n_cycles"][near] > 0


def test_session_json_is_valid_and_free_of_nan(processed, normbands: dict, tmp_path: Path) -> None:
    session, results = processed
    summary = aggregate_session(session, results, normbands=normbands)
    path = summary.write_json(tmp_path / "session.json")
    text = path.read_text(encoding="utf-8")
    assert "NaN" not in text
    assert "Infinity" not in text
    document = json.loads(text)  # would raise on a bare NaN token
    assert document["schema"] == "openacl.session.v1"
    assert document["operated_side"] == "R"
    assert document["metrics"]["stance_pct"]["R"]["mean"] > 0
    assert document["quality"]["n_passes_ok"] == 6

    def no_nan(node) -> None:
        if isinstance(node, dict):
            for value in node.values():
                no_nan(value)
        elif isinstance(node, list):
            for value in node:
                no_nan(value)
        elif isinstance(node, float):
            assert math.isfinite(node)

    no_nan(document)


def test_a_failing_pass_does_not_stop_the_session(
    fake_session: FakeSession, normbands: dict
) -> None:
    broken = fake_session.root / "derived" / "A_pass03" / "kinematics.npz"
    broken.write_bytes(b"not an npz")
    session = load_session(fake_session.root)
    results = process_session(session, normbands=normbands)
    assert len(results) == 6
    failed = [r for r in results if not r.ok]
    assert [r.name for r in failed] == ["A_pass03"]
    summary = aggregate_session(session, results, normbands=normbands)
    assert summary.quality["n_passes_ok"] == 5
    assert "A_pass03" in summary.quality["failed_passes"]
    assert summary.metrics["stance_pct"]["R"].n > 0


def test_subject_mdc_yaml_is_read_when_present(tmp_path: Path) -> None:
    path = tmp_path / "mdc.yaml"
    path.write_text(
        "parameters:\n"
        "  peak_knee_flexion_swing_deg:\n"
        "    value: 3.4\n"
        "    unit: deg\n"
        "    source: eigene Wiederholungsmessung\n",
        encoding="utf-8",
    )
    table = load_subject_mdc(path)
    assert table["peak_knee_flexion_swing_deg"].value == pytest.approx(3.4)
    assert table["peak_knee_flexion_swing_deg"].origin == "own"
    assert load_subject_mdc(tmp_path / "missing.yaml") == {}


def test_pooled_curves_have_the_expected_shape(processed) -> None:
    _session, results = processed
    pooled, _ = pool_cycles(results, "camera_near")
    mean_curve = pooled.mean_curve_deg("knee_flexion_deg", "R")
    sd_curve = pooled.sd_curve_deg("knee_flexion_deg", "R")
    assert mean_curve is not None and mean_curve.shape == (101,)
    assert sd_curve is not None and sd_curve.shape == (101,)
    assert np.isfinite(mean_curve).all()

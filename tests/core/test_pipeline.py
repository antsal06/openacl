"""End-to-end tests of the gait-core pipeline."""

from __future__ import annotations

import numpy as np
import pytest

from openacl.core import analyze
from openacl.core.normband import NormBand
from openacl.core.pipeline import filter_result
from tests.core.synthetic import make_synthetic_gait


def test_analyze_returns_all_sections():
    result, truth = make_synthetic_gait(unit="m")
    analysis = analyze(result, operated_side="L")
    assert analysis.events.heel_strikes_L.size == truth.heel_strikes["L"].size
    assert analysis.cycles.n_points == 101
    assert analysis.spatiotemporal.both.stride_time_s.mean == pytest.approx(
        truth.stride_time_s, abs=0.02
    )
    assert analysis.symmetry.operated_side == "L"
    assert analysis.deviation.gvs_deg == {"L": {}, "R": {}}
    assert analysis.operated_side == "L"
    assert analysis.meta["backend"] == "synthetic"
    assert analysis.meta["filter"]["cutoff_hz"] == 6.0


def test_discrete_knee_values_match_the_generator():
    result, truth = make_synthetic_gait()
    analysis = analyze(result)
    for side in ("L", "R"):
        values = analysis.discrete_deg[side]
        assert values["peak_knee_flexion_swing_deg"] == pytest.approx(
            truth.peak_knee_swing_deg[side], abs=1.0
        )
        assert values["peak_knee_flexion_loading_deg"] == pytest.approx(
            truth.peak_knee_stance_deg[side], abs=1.0
        )
        assert values["knee_flexion_at_initial_contact_deg"] < 10.0


def test_warning_when_fewer_than_ten_valid_cycles():
    result, _ = make_synthetic_gait(n_cycles=5)
    analysis = analyze(result)
    assert any("valid gait cycles" in w for w in analysis.warnings)
    assert analysis.n_valid_cycles["L"] < 10


def test_no_cycle_count_warning_for_a_long_recording():
    result, _ = make_synthetic_gait(n_cycles=25)
    analysis = analyze(result)
    assert not any("valid gait cycles" in w for w in analysis.warnings)
    assert analysis.n_valid_cycles["R"] >= 20


def test_warning_for_the_low_confidence_camera_far_leg():
    result, _ = make_synthetic_gait(camera_near_side="R", confidence_far_side=0.35)
    analysis = analyze(result)
    assert any("camera-far leg L" in w for w in analysis.warnings)


def test_warning_when_the_walking_direction_was_estimated():
    result, _ = make_synthetic_gait(declare_direction=False)
    analysis = analyze(result)
    assert any("walking direction was estimated" in w for w in analysis.warnings)


def test_warning_when_the_backend_reports_no_confidence():
    result, _ = make_synthetic_gait()
    result.confidence = {}
    analysis = analyze(result)
    assert any("no per-keypoint confidence" in w for w in analysis.warnings)


def test_filter_result_does_not_touch_the_input():
    result, _ = make_synthetic_gait(noise_deg=2.0, seed=11)
    before = result.angles_deg["knee_flexion_deg_L"].copy()
    filtered = filter_result(result)
    assert np.allclose(result.angles_deg["knee_flexion_deg_L"], before)
    assert np.std(filtered.angles_deg["knee_flexion_deg_L"] - before) > 0
    assert filtered.meta["gait_core_filter"]["order"] == 4


def test_pipeline_is_robust_against_noise_and_gaps():
    result, truth = make_synthetic_gait(
        unit="m", noise_px=2.0, noise_deg=1.5, nan_gaps_s=((4.0, 4.2),), seed=5
    )
    analysis = analyze(result)
    assert analysis.spatiotemporal.both.stance_pct.mean == pytest.approx(60.0, abs=2.0)
    assert analysis.spatiotemporal.both.walking_speed_m_s.mean == pytest.approx(
        truth.walking_speed_m_s, abs=0.1
    )
    assert abs(analysis.symmetry.symmetry_index_pct["stance_pct"]) < 3.0


def test_analyze_with_norm_bands_produces_gps():
    result, _ = make_synthetic_gait()
    first = analyze(result)
    bands = {
        channel: NormBand(
            mean=first.cycles.mean_curve_deg(channel, "L"),
            sd=np.full(101, 5.0),
            n=30,
            source="synthetic reference",
        )
        for channel in first.cycles.channels("L")
    }
    analysis = analyze(result, normbands=bands)
    assert analysis.deviation.gps_deg["L"] == pytest.approx(0.0, abs=1e-9)
    assert np.isfinite(analysis.deviation.gps_deg["R"])
    assert analysis.deviation.missing_bands == ()


def test_gait_core_does_not_import_a_backend():
    """ADR-0007: layer 3 must stay backend-independent."""
    import ast
    import pathlib

    core_dir = pathlib.Path(__file__).resolve().parents[2] / "src" / "openacl" / "core"
    modules: list[str] = []
    for path in sorted(core_dir.glob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
    assert modules, "no imports found, the test would be vacuous"
    assert not [m for m in modules if m.startswith("openacl.backends")]
    assert not [m for m in modules if m.split(".")[0] in {"torch", "tensorflow", "sklearn"}]

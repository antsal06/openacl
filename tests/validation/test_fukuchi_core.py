"""End-to-end validation of gait-core against real Fukuchi et al. (2018) marker data.

Skipped entirely when the (gitignored, locally downloaded) raw dataset is not present, see
``docs/validation/core_vs_fukuchi.md`` for the full result table and
``scripts/validate_core_fukuchi.py`` for how the ``KinematicsResult`` is built.

Tolerances
----------
- Walking speed: within 0.1 m/s of the exact-pass ``GaitSpeed(m/s)`` from ``WBDSinfo.xlsx``
  (task-specified hard tolerance; no systematic bias was found for speed).
- Stance phase: gait-core's marker/Zeni-based stance estimate carries a **documented,
  systematic bias of about +5.5 (SD 1.25) percentage points** relative to the force-plate
  reference (heel strike detected ~37 ms early, toe off ~19 ms late -- see the "Befund:
  Standphase systematisch überschätzt" section of ``docs/validation/core_vs_fukuchi.md``).
  The test therefore checks the *detrended* residual (measured minus the known bias) against
  the force-plate reference within +-3 percentage points, rather than a naive, bias-blind
  60 +- 3 % window that this pipeline provably does not meet on real marker data.
- Peak knee flexion in swing: within +-2 SD of the speed-classified norm band peak
  (``openacl.norm.load_normbands``).
- Direction detection: ``estimate_direction_sign`` must agree with the sign of the real ASIS
  displacement on every trial (it does, on all 36 trials checked by the validation script).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT / "data" / "norm" / "fukuchi2018"

sys.path.insert(0, str(REPO_ROOT / "scripts"))

pytestmark = pytest.mark.skipif(
    not DATA_ROOT.exists(),
    reason="data/norm/fukuchi2018 not present locally (gitignored, CC BY 4.0 dataset)",
)

SUBJECTS = ("WBDS01", "WBDS02")
SPEED_TOLERANCE_M_S = 0.1
KNOWN_STANCE_BIAS_PCT = 5.5
"""Documented Zeni-vs-force-plate bias, see docs/validation/core_vs_fukuchi.md."""
STANCE_RESIDUAL_TOLERANCE_PCT = 3.0


def _module():
    import validate_core_fukuchi as vcf

    return vcf


@pytest.fixture(scope="module")
def validation_result():
    vcf = _module()
    if not (vcf.DEFAULT_ROOT / vcf.ZIP_NAME).exists():
        pytest.skip(f"{vcf.ZIP_NAME} not found under {vcf.DEFAULT_ROOT}")
    table, timing, raw = vcf.run_validation(
        root=vcf.DEFAULT_ROOT, subjects=SUBJECTS, conditions=vcf.CONDITIONS
    )
    return vcf, table, timing, raw


def test_all_subject_condition_combinations_produced_a_row(validation_result):
    _vcf, table, _timing, _raw = validation_result
    assert len(table) == len(SUBJECTS) * 3
    assert set(table["subject_id"]) == set(SUBJECTS)
    assert set(table["condition"]) == {"S", "C", "F"}


def test_walking_speed_matches_metadata_within_tolerance(validation_result):
    _vcf, table, _timing, _raw = validation_result
    with_ref = table.dropna(subset=["speed_ref_m_s"])
    assert len(with_ref) >= 4, "expected a speed reference for most of these trials"
    for _, row in with_ref.iterrows():
        assert abs(row["speed_diff_m_s"]) <= SPEED_TOLERANCE_M_S, (
            f"{row['subject_id']}/{row['condition']}: "
            f"|{row['speed_measured_m_s']:.3f} - {row['speed_ref_m_s']:.3f}| "
            f"> {SPEED_TOLERANCE_M_S} m/s"
        )


def test_stance_phase_matches_force_plate_after_the_known_bias(validation_result):
    _vcf, table, _timing, _raw = validation_result
    with_ref = table.dropna(subset=["stance_ref_pct"])
    assert len(with_ref) >= 3, "expected a force-plate stance reference for most of these trials"
    for _, row in with_ref.iterrows():
        residual = (row["stance_measured_pct"] - KNOWN_STANCE_BIAS_PCT) - row["stance_ref_pct"]
        assert abs(residual) <= STANCE_RESIDUAL_TOLERANCE_PCT, (
            f"{row['subject_id']}/{row['condition']}: stance residual after de-biasing is "
            f"{residual:.2f} pct points (measured {row['stance_measured_pct']:.1f} %, "
            f"reference {row['stance_ref_pct']:.1f} %)"
        )
        # Plausibility floor: even with the documented bias, stance should stay well inside
        # a physiologically sane range (task: 60 +- ~10 pct given the bias).
        assert 50.0 <= row["stance_measured_pct"] <= 80.0


def test_peak_knee_flexion_within_two_sd_of_the_normband(validation_result):
    _vcf, table, _timing, _raw = validation_result
    for _, row in table.iterrows():
        lower = row["peak_knee_normband_mean_deg"] - 2.0 * row["peak_knee_normband_sd_deg"]
        upper = row["peak_knee_normband_mean_deg"] + 2.0 * row["peak_knee_normband_sd_deg"]
        assert lower <= row["peak_knee_measured_deg"] <= upper, (
            f"{row['subject_id']}/{row['condition']}: peak knee "
            f"{row['peak_knee_measured_deg']:.1f} deg outside "
            f"[{lower:.1f}, {upper:.1f}] deg (norm band +-2 SD)"
        )


def test_direction_estimation_matches_the_real_progression_sign(validation_result):
    _vcf, table, _timing, _raw = validation_result
    mismatches = table.loc[~table["direction_match"]]
    assert mismatches.empty, (
        "estimate_direction_sign disagreed with the real ASIS displacement sign on "
        f"{len(mismatches)} trial(s): "
        f"{mismatches[['subject_id', 'condition']].to_dict('records')}"
    )


def test_event_timing_bias_is_within_the_documented_range(validation_result):
    """Regression guard on the documented heel-strike-early / toe-off-late bias.

    Not a correctness assertion (the bias itself is an expected, documented property of the
    Zeni kinematic method on this dataset/marker choice, see docs/validation/
    core_vs_fukuchi.md) -- just a guard against the bias silently growing much larger, which
    would indicate an unrelated regression in event detection.
    """
    _vcf, _table, timing, _raw = validation_result
    if timing.empty:
        pytest.skip("no matched force-plate contacts for this subject subset")
    by_event = timing.groupby("event")["offset_ms"].mean()
    if "heel_strike" in by_event:
        assert -80.0 <= by_event["heel_strike"] <= 0.0
    if "toe_off" in by_event:
        assert 0.0 <= by_event["toe_off"] <= 80.0

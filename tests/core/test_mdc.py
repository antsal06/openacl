"""Tests for the MDC / ICC computations."""

from __future__ import annotations

import numpy as np
import pytest

from openacl.core.mdc import (
    DEFAULT_MDC,
    default_mdc,
    icc_2_1,
    is_above_mdc,
    mdc_table_from_sessions,
    reliability_from_repeats,
)

# Shrout & Fleiss 1979, Table 1 (6 targets x 4 judges). Published: ICC(2,1) = 0.29.
SHROUT_FLEISS = np.array(
    [
        [9, 2, 5, 8],
        [6, 1, 3, 2],
        [8, 4, 6, 8],
        [7, 1, 2, 6],
        [10, 5, 6, 9],
        [6, 2, 4, 7],
    ],
    dtype=float,
)


def test_icc_2_1_matches_shrout_fleiss_table_1():
    assert icc_2_1(SHROUT_FLEISS) == pytest.approx(0.29, abs=0.005)


def test_reliability_matches_hand_computed_example():
    """3 targets x 2 sessions, computed by hand.

    Row means 10.5/20.5/30.5, column means 20/21, grand mean 20.5:
    MS_R = 200, MS_C = 1.5, MS_E = 0  ->  ICC = 200 / (200 + 2 * 1.5 / 3) = 200/201.
    SD_pooled = sqrt(401.5 / 5) = 8.96103, SEM = SD * sqrt(1 - ICC) = 0.6320621,
    MDC95 = 1.959964 * sqrt(2) * SEM = 1.7519546.
    """
    values = np.array([[10.0, 11.0], [20.0, 21.0], [30.0, 31.0]])
    result = reliability_from_repeats(values, unit="deg")
    assert result.icc_2_1 == pytest.approx(200.0 / 201.0, rel=1e-9)
    assert result.sd_pooled == pytest.approx(8.9610267, rel=1e-6)
    assert result.sem == pytest.approx(0.6320621, rel=1e-6)
    assert result.mdc95 == pytest.approx(1.7519546, rel=1e-6)
    assert result.n_targets == 3
    assert result.n_sessions == 2
    assert result.unit == "deg"


def test_mdc95_is_1_96_times_sqrt2_times_sem():
    rng = np.random.default_rng(7)
    values = rng.normal(50.0, 5.0, size=(20, 3))
    result = reliability_from_repeats(values)
    assert result.mdc95 == pytest.approx(1.959964 * np.sqrt(2) * result.sem, rel=1e-12)


def test_perfect_agreement_gives_zero_mdc():
    values = np.array([[1.0, 1.0], [5.0, 5.0], [9.0, 9.0], [13.0, 13.0]])
    result = reliability_from_repeats(values)
    assert result.icc_2_1 == pytest.approx(1.0)
    assert result.mdc95 == pytest.approx(0.0, abs=1e-12)


def test_icc_requires_complete_matrix():
    with pytest.raises(ValueError):
        icc_2_1(np.array([[1.0, np.nan], [2.0, 3.0]]))
    with pytest.raises(ValueError):
        icc_2_1(np.array([1.0, 2.0, 3.0]))


def test_is_above_mdc():
    assert is_above_mdc(10.0, 9.2)
    assert is_above_mdc(-10.0, 9.2)
    assert not is_above_mdc(9.0, 9.2)
    assert not is_above_mdc(9.2, 9.2)
    assert not is_above_mdc(float("nan"), 9.2)


def test_literature_defaults_carry_source_and_placeholder_flag():
    knee = default_mdc("peak_knee_flexion_deg")
    assert knee is not None
    assert knee.value == pytest.approx(9.2)
    assert knee.unit == "deg"
    assert "28288331" in knee.source
    assert not knee.placeholder
    assert DEFAULT_MDC["stance_pct"].value == pytest.approx(5.0)
    assert DEFAULT_MDC["stance_pct"].placeholder
    assert default_mdc("does_not_exist") is None
    for name, entry in DEFAULT_MDC.items():
        assert entry.source, f"{name} has no source"


def test_mdc_table_from_mapping_and_array():
    matrices = {"stance_pct": np.array([[60.0, 61.0], [58.0, 59.5], [62.0, 61.0]])}
    table = mdc_table_from_sessions(matrices)
    assert set(table) == {"stance_pct"}
    arr = np.stack([matrices["stance_pct"][:, 0], matrices["stance_pct"][:, 1]])[:, :, None]
    table2 = mdc_table_from_sessions(arr, parameter_names=["stance_pct"])
    assert table2["stance_pct"].mdc95 == pytest.approx(table["stance_pct"].mdc95)

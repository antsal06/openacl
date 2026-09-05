"""Loader test for the Van Criekinge 2023 post-processed Excel export (synthetic, no network)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from openacl.core.normband import N_POINTS
from openacl.norm import vancriekinge
from openacl.schema import ANGLE_CHANNELS

N_RAW = vancriekinge.N_RAW_POINTS


def _write_workbook(path: Path, n_subjects: int = 4) -> Path:
    """Write a miniature workbook with the real sheet and column layout."""
    pct = np.linspace(0.0, 100.0, N_RAW)
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"note": ["ReadMe sheet, must be ignored"]}).to_excel(
            writer, sheet_name="ReadMe", index=False
        )
        for i in range(1, n_subjects + 1):
            frame = pd.DataFrame(
                {
                    "AnkleAngles": 8.0 * np.sin(2 * np.pi * pct / 100.0),
                    "KneeAngles": (55.0 + i) * np.exp(-(((pct - 72) / 12) ** 2)),
                    "HipAngles": 30.0 * np.cos(2 * np.pi * pct / 100.0),
                    "PelvisAngles": 10.0 + np.zeros(N_RAW),
                    "GRF_vert": np.zeros(N_RAW),
                }
            )
            frame.to_excel(writer, sheet_name=f"Sub{i:02d}", index=False)
    return path


def test_resample_to_pct_endpoints() -> None:
    raw = np.linspace(0.0, 10.0, N_RAW)
    out = vancriekinge.resample_to_pct(raw)
    assert out.shape == (N_POINTS,)
    assert out[0] == pytest.approx(0.0)
    assert out[-1] == pytest.approx(10.0)
    assert out[50] == pytest.approx(5.0, abs=0.05)


def test_load_angles_long_format(tmp_path: Path) -> None:
    _write_workbook(tmp_path / vancriekinge.EXCEL_NAME)
    long = vancriekinge.load_angles(tmp_path)
    assert long["dataset"].unique().tolist() == ["vancriekinge2023"]
    assert set(long["subject_id"]) == {"Sub01", "Sub02", "Sub03", "Sub04"}
    assert set(long["channel"]) <= set(ANGLE_CHANNELS)
    assert set(long["side"]) == {"B"}, "the public export is already pooled over sides"
    assert long["speed_m_s"].isna().all(), "the public export carries no walking speed"
    assert len(long) == 4 * 4 * N_POINTS


def test_load_angles_keeps_the_clinical_sign(tmp_path: Path) -> None:
    _write_workbook(tmp_path / vancriekinge.EXCEL_NAME)
    long = vancriekinge.load_angles(tmp_path)
    knee = long[(long["channel"] == "knee_flexion_deg") & (long["subject_id"] == "Sub01")]
    assert knee["value_deg"].max() == pytest.approx(56.0, abs=1.0)
    peak_pct = knee["pct"].to_numpy()[int(knee["value_deg"].to_numpy().argmax())]
    assert 55 <= peak_pct <= 90


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        vancriekinge.load_angles(tmp_path)

"""Loader tests against a synthetic dataset in the Fukuchi ASCII layout (no network)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from openacl.norm import fukuchi
from openacl.schema import ANGLE_CHANNELS

from .conftest import write_angle_file


def test_read_angle_file_shape(tmp_path: Path) -> None:
    path = write_angle_file(tmp_path / "WBDS01walkOCang.txt", knee_peak_deg=60.0)
    frame = fukuchi.read_angle_file(path)
    assert len(frame) == fukuchi.N_PCT
    assert frame["Time"].iloc[0] == 0
    assert frame["Time"].iloc[-1] == 100


def test_read_angle_file_rejects_wrong_length(tmp_path: Path) -> None:
    path = write_angle_file(tmp_path / "WBDS01walkOCang.txt", knee_peak_deg=60.0)
    text = path.read_text().splitlines()
    path.write_text("\n".join(text[:-5]))
    with pytest.raises(ValueError, match="expected 101 rows"):
        fukuchi.read_angle_file(path)


def test_angle_file_to_long_channels_and_sides(tmp_path: Path) -> None:
    path = write_angle_file(tmp_path / "WBDS07walkOFang.txt", knee_peak_deg=62.0)
    long = fukuchi.angle_file_to_long(path)
    assert long["subject_id"].unique().tolist() == ["WBDS07"]
    assert long["trial_id"].unique().tolist() == ["OF"]
    assert set(long["channel"]) <= set(ANGLE_CHANNELS)
    sided = long[long["channel"] == "knee_flexion_deg"]
    assert set(sided["side"]) == {"L", "R"}
    assert len(sided) == 2 * fukuchi.N_PCT
    # pelvis has no side in the schema, the loader pools the two Fukuchi columns
    assert set(long[long["channel"] == "pelvis_tilt_deg"]["side"]) == {"B"}


def test_angle_file_to_long_rejects_foreign_name(tmp_path: Path) -> None:
    path = write_angle_file(tmp_path / "something_else.txt", knee_peak_deg=60.0)
    with pytest.raises(ValueError, match="not a Fukuchi angle file name"):
        fukuchi.angle_file_to_long(path)


def test_clinical_sign_convention(tmp_path: Path) -> None:
    """Knee flexion peaks positive in swing; ankle is most negative around toe-off."""
    path = write_angle_file(tmp_path / "WBDS01walkOCang.txt", knee_peak_deg=63.0)
    long = fukuchi.angle_file_to_long(path)
    knee = long[(long["channel"] == "knee_flexion_deg") & (long["side"] == "R")]
    peak_index = int(knee["value_deg"].to_numpy().argmax())
    assert knee["value_deg"].max() == pytest.approx(63.0, abs=0.5)
    assert 55 <= knee["pct"].to_numpy()[peak_index] <= 90
    ankle = long[(long["channel"] == "ankle_dorsiflexion_deg") & (long["side"] == "R")]
    trough_index = int(ankle["value_deg"].to_numpy().argmin())
    assert 50 <= ankle["pct"].to_numpy()[trough_index] <= 75


def test_load_subject_info(fukuchi_root: Path) -> None:
    info = fukuchi.load_subject_info(fukuchi_root)
    assert len(info) == 6
    assert info["subject_id"].tolist() == [f"WBDS{i:02d}" for i in range(1, 7)]
    assert info["height_m"].between(1.6, 2.0).all()
    assert info["leg_length_measured"].all()


def test_load_subject_info_falls_back_for_implausible_leg_length(fukuchi_root: Path) -> None:
    import pandas as pd

    info_path = fukuchi_root / "WBDSinfo.xlsx"
    raw = pd.read_excel(info_path)
    raw.loc[raw["Subject"] == 1, "LegLength"] = 1.91  # the real file contains such an outlier
    raw.to_excel(info_path, index=False)
    info = fukuchi.load_subject_info(fukuchi_root).set_index("subject_id")
    assert not info.loc["WBDS01", "leg_length_measured"]
    assert info.loc["WBDS01", "leg_length_m"] == pytest.approx(
        0.53 * info.loc["WBDS01", "height_m"]
    )


def test_load_angles_long_format(fukuchi_root: Path) -> None:
    long = fukuchi.load_angles(fukuchi_root, conditions=("overground",))
    assert list(long.columns) == fukuchi.LONG_COLUMNS
    assert long["dataset"].unique().tolist() == ["fukuchi2018"]
    assert set(long["trial_id"]) == {"OS", "OC", "OF"}
    assert set(long["condition"]) == {"overground"}
    assert long["speed_m_s"].notna().all()
    assert long["pct"].min() == 0.0 and long["pct"].max() == 100.0
    # 6 subjects x 3 conditions x (3 sided channels x 2 sides + 1 pooled) x 101 points
    assert len(long) == 6 * 3 * 7 * fukuchi.N_PCT


def test_load_angles_speed_is_the_mean_over_passes(fukuchi_root: Path) -> None:
    long = fukuchi.load_angles(fukuchi_root)
    comfortable = long[(long["subject_id"] == "WBDS03") & (long["trial_id"] == "OC")]
    assert comfortable["speed_m_s"].unique() == pytest.approx([1.26])


def test_stride_metrics_from_synthetic_contacts() -> None:
    fs = 100.0
    # 1.0 s stride, 0.6 s stance per foot, feet offset by half a stride
    left = [(0, 60), (100, 160), (200, 260)]
    right = [(-50, 10), (50, 110), (150, 210)]
    strides = fukuchi._stride_metrics(left, right, fs, speed_m_s=1.2)
    assert strides
    for stride in strides:
        assert stride["stride_time_s"] == pytest.approx(1.0)
        assert stride["stance_pct"] == pytest.approx(60.0)
        assert stride["cadence_steps_min"] == pytest.approx(120.0)
        assert stride["step_length_m"] == pytest.approx(0.6)
        # two double-support phases of 0.1 s each in a 1.0 s cycle
        assert stride["double_support_pct"] == pytest.approx(20.0)


def test_stride_metrics_skips_strides_with_a_missed_step() -> None:
    left = [(0, 60), (100, 160)]
    right = [(50, 110)]  # no contralateral contact bracketing the ipsilateral IC
    assert fukuchi._stride_metrics(left, right, 100.0, 1.2) == []


def test_contacts_debounces_short_spikes() -> None:
    force = np.zeros(500)
    force[100:200] = 600.0
    force[300:305] = 600.0  # too short to be a stance phase
    contacts = fukuchi._contacts(force, threshold_n=30.0, min_samples=20)
    assert contacts == [(100, 200)]


def test_plates_for_foot() -> None:
    assert fukuchi._plates_for_foot("FP4_5, FP1") == [1, 4, 5]
    assert fukuchi._plates_for_foot("FP2") == [2]
    assert fukuchi._plates_for_foot("--") == []
    assert fukuchi._plates_for_foot(None) == []

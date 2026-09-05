"""Tests for openacl.health.export: unit conversion, timezone parsing, zip vs xml, filtering."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from openacl.health.export import EXPORT_COLUMNS, _summarize_device, load_gait_export
from tests.health.synthetic import SyntheticRecord, write_export_xml, write_export_zip

EXPECTED_COUNTS = {
    "walking_speed_m_s": 9,
    "step_length_m": 9,
    "double_support_pct": 8,
    "walking_asymmetry_pct": 6,
    "walking_steadiness_pct": 3,
    "step_count": 3,
}


def test_columns_and_counts(export_xml_path: Path):
    df = load_gait_export(export_xml_path)
    assert list(df.columns) == list(EXPORT_COLUMNS)
    counts = df.groupby("metric")["value"].count().to_dict()
    assert counts == EXPECTED_COUNTS


def test_ignores_non_gait_record_types(export_xml_path: Path):
    df = load_gait_export(export_xml_path)
    assert "HeartRate" not in " ".join(df["metric"].unique())
    assert set(df["metric"]) == set(EXPECTED_COUNTS)


def test_walking_speed_unit_conversion(export_xml_path: Path):
    df = load_gait_export(export_xml_path)
    speed = df[df["metric"] == "walking_speed_m_s"]
    assert (speed["unit"] == "m/s").all()
    # 3.6 km/hr -> 1.0 m/s
    assert np.isclose(speed["value"], 1.0, atol=1e-6).any()
    # the one raw-m/s record (1.1) must pass through unchanged
    assert np.isclose(speed["value"], 1.1, atol=1e-6).any()


def test_step_length_unit_conversion(export_xml_path: Path):
    df = load_gait_export(export_xml_path)
    step = df[df["metric"] == "step_length_m"]
    assert (step["unit"] == "m").all()
    # 60 cm -> 0.6 m
    assert np.isclose(step["value"], 0.6, atol=1e-6).any()
    # the one raw-m record (0.66) must pass through unchanged
    assert np.isclose(step["value"], 0.66, atol=1e-6).any()


@pytest.mark.parametrize(
    "metric,raw_fraction,expected_pct",
    [
        ("double_support_pct", 0.20, 20.0),
        ("walking_asymmetry_pct", 0.0, 0.0),
        ("walking_steadiness_pct", 0.95, 95.0),
    ],
)
def test_percentage_fraction_to_percent(
    export_xml_path: Path, metric: str, raw_fraction: float, expected_pct: float
):
    df = load_gait_export(export_xml_path)
    sub = df[df["metric"] == metric]
    assert (sub["unit"] == "pct").all()
    assert np.isclose(sub["value"], expected_pct, atol=1e-6).any()


def test_step_count_passthrough(export_xml_path: Path):
    df = load_gait_export(export_xml_path)
    counts = df[df["metric"] == "step_count"]
    assert (counts["unit"] == "count").all()
    assert set(counts["value"]) == {50.0, 120.0, 80.0}


def test_timezone_offsets_parsed_to_utc(export_xml_path: Path):
    df = load_gait_export(export_xml_path)
    assert df["start"].dt.tz is not None
    assert str(df["start"].dt.tz) == "UTC"
    # 2026-02-10 08:00:00 +0100 -> 07:00:00 UTC
    cet_row = df[(df["metric"] == "step_length_m") & (df["value"].round(2) == 0.6)].iloc[0]
    assert cet_row["start"] == pd.Timestamp("2026-02-10 07:00:00", tz="UTC")
    # later records use +0200 (CEST offset) -> UTC hour shifts by 2, not 1
    cest_rows = df[(df["metric"] == "walking_speed_m_s") & (df["start"].dt.month == 3)]
    assert not cest_rows.empty
    assert (cest_rows["start"].dt.hour == 6).all()


def test_source_name_and_device(export_xml_path: Path):
    df = load_gait_export(export_xml_path)
    assert (df["source_name"] == "iPhone von Anton").all()
    assert (df["device"] == "iPhone (iPhone13,2)").all()


def test_summarize_device_missing():
    assert _summarize_device(None) == ""
    assert _summarize_device("") == ""
    assert _summarize_device("garbage, no fields") == ""


def test_zip_matches_xml(export_xml_path: Path, export_zip_path: Path):
    from_xml = load_gait_export(export_xml_path)
    from_zip = load_gait_export(export_zip_path)
    pd.testing.assert_frame_equal(from_xml, from_zip)


def test_export_cda_xml_is_not_picked(tmp_path: Path):
    # export_cda.xml only contains a bare <HealthData/> with no records; if the loader
    # accidentally picked it, the result would be empty instead of the real record set.
    zip_path = write_export_zip(tmp_path / "export.zip")
    df = load_gait_export(zip_path)
    assert len(df) == sum(EXPECTED_COUNTS.values())


def test_empty_export_returns_typed_empty_dataframe(tmp_path: Path):
    path = write_export_xml(tmp_path / "export.xml", records=[])
    df = load_gait_export(path)
    assert df.empty
    assert list(df.columns) == list(EXPORT_COLUMNS)


def test_unknown_unit_raises(tmp_path: Path):
    bad = SyntheticRecord(
        "HKQuantityTypeIdentifierWalkingSpeed",
        "mph",
        "3.0",
        "2026-02-10 08:00:00 +0100",
        "2026-02-10 08:00:05 +0100",
    )
    path = write_export_xml(tmp_path / "export.xml", records=[bad])
    with pytest.raises(ValueError, match="mph"):
        load_gait_export(path)

"""End-to-end test of `python -m openacl.health` via its `main()` entry point."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from openacl.health.__main__ import main


def test_main_writes_all_outputs(export_xml_path: Path, tmp_path: Path):
    out_dir = tmp_path / "derived"
    rc = main([str(export_xml_path), "--out", str(out_dir), "--surgery-date", "2026-03-01"])
    assert rc == 0

    daily_path = out_dir / "health_daily.parquet"
    summary_path = out_dir / "health_summary.json"
    png_path = out_dir / "health_trends.png"
    assert daily_path.exists()
    assert summary_path.exists()
    assert png_path.exists()
    assert png_path.stat().st_size > 0

    daily = pd.read_parquet(daily_path)
    assert "rolling_median_7d" in daily.columns
    assert not daily.empty

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["surgery_date"] == "2026-03-01"
    assert "walking_speed_m_s" in summary["metrics"]


def test_main_without_surgery_date(export_xml_path: Path, tmp_path: Path):
    out_dir = tmp_path / "derived_no_op"
    rc = main([str(export_xml_path), "--out", str(out_dir)])
    assert rc == 0
    summary = json.loads((out_dir / "health_summary.json").read_text(encoding="utf-8"))
    assert summary["surgery_date"] is None
    assert (out_dir / "health_trends.png").exists()


def test_main_missing_source_returns_error(tmp_path: Path):
    rc = main([str(tmp_path / "does_not_exist.xml"), "--out", str(tmp_path / "out")])
    assert rc == 1

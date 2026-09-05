"""Tests for openacl.health.plot: the PNG gets written, with and without a surgery date."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from openacl.health.daily import rolling_median_7d
from openacl.health.export import load_gait_export
from openacl.health.plot import _period_bands, plot_trends


def test_plot_trends_writes_png_with_surgery_date(export_xml_path: Path, tmp_path: Path):
    df = load_gait_export(export_xml_path)
    daily = rolling_median_7d(df)
    out = tmp_path / "trends.png"
    plot_trends(daily, out, surgery_date=date(2026, 3, 1))
    assert out.exists()
    assert out.stat().st_size > 0


def test_plot_trends_writes_png_without_surgery_date(export_xml_path: Path, tmp_path: Path):
    df = load_gait_export(export_xml_path)
    daily = rolling_median_7d(df)
    out = tmp_path / "trends_no_op.png"
    plot_trends(daily, out, surgery_date=None)
    assert out.exists()
    assert out.stat().st_size > 0


def test_plot_trends_handles_empty_daily_frame(tmp_path: Path):
    import pandas as pd

    empty = pd.DataFrame(
        columns=["metric", "date", "mean", "median", "sd", "n", "rolling_median_7d"]
    )
    out = tmp_path / "trends_empty.png"
    plot_trends(empty, out, surgery_date=date(2026, 3, 1))
    assert out.exists()


def test_period_bands_clipped_to_data_range():
    surgery = date(2026, 3, 1)
    data_min = date(2026, 1, 1)
    data_max = date(2026, 3, 20)  # inside the "0-6 Wochen post-OP" band, well short of "> 26"
    bands = _period_bands(surgery, data_min, data_max)
    labels = [label for _, _, label in bands]
    assert labels == ["vor OP", "0-6 Wochen post-OP"]
    assert bands[0][0] == data_min
    assert bands[-1][1] == data_max

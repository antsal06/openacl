"""Tests for openacl.health.daily: day/week aggregation, rolling median, period comparison."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from openacl.health.daily import (
    PERIOD_ORDER,
    MetricStat,
    assign_period,
    daily_stats,
    period_summary,
    period_summary_json,
    rolling_median_7d,
    weekly_stats,
)

UTC = "UTC"


def _row(metric: str, local_date: str, value: float, hour: int = 8) -> dict:
    return {
        "metric": metric,
        "start": pd.Timestamp(f"{local_date} {hour:02d}:00:00", tz=UTC),
        "end": pd.Timestamp(f"{local_date} {hour:02d}:00:05", tz=UTC),
        "value": value,
        "unit": "m/s",
        "source_name": "iPhone von Anton",
        "device": "iPhone (test)",
    }


def _frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


# --- MetricStat -------------------------------------------------------------------------


def test_metric_stat_from_values():
    stat = MetricStat.from_values([1.0, 2.0, 3.0, np.nan])
    assert stat.mean == pytest.approx(2.0)
    assert stat.median == pytest.approx(2.0)
    assert stat.sd == pytest.approx(1.0)
    assert stat.n == 3


def test_metric_stat_empty():
    stat = MetricStat.from_values([np.nan, np.nan])
    assert stat.n == 0
    assert np.isnan(stat.mean)
    assert np.isnan(stat.median)


def test_metric_stat_single_value_sd_is_nan():
    stat = MetricStat.from_values([5.0])
    assert stat.n == 1
    assert np.isnan(stat.sd)


# --- assign_period -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "offset_days,expected",
    [
        (-1, "vor OP"),
        (0, "0-6 Wochen post-OP"),
        (6 * 7 - 1, "0-6 Wochen post-OP"),
        (6 * 7, "6-12 Wochen post-OP"),
        (12 * 7 - 1, "6-12 Wochen post-OP"),
        (12 * 7, "12-26 Wochen post-OP"),
        (26 * 7 - 1, "12-26 Wochen post-OP"),
        (26 * 7, "> 26 Wochen post-OP"),
    ],
)
def test_assign_period_boundaries(offset_days: int, expected: str):
    surgery = date(2026, 3, 1)
    day = surgery + pd.Timedelta(days=offset_days).to_pytimedelta()
    assert assign_period(day, surgery) == expected


# --- daily_stats / weekly_stats ------------------------------------------------------------


def test_daily_stats_mean_median_n():
    rows = [
        _row("walking_speed_m_s", "2026-02-10", 1.0),
        _row("walking_speed_m_s", "2026-02-10", 2.0),
        _row("walking_speed_m_s", "2026-02-10", 3.0),
        _row("walking_speed_m_s", "2026-02-11", 10.0),
    ]
    out = daily_stats(_frame(rows), local_tz=UTC)
    day1 = out[out["date"] == date(2026, 2, 10)].iloc[0]
    assert day1["mean"] == pytest.approx(2.0)
    assert day1["median"] == pytest.approx(2.0)
    assert day1["n"] == 3
    day2 = out[out["date"] == date(2026, 2, 11)].iloc[0]
    assert day2["mean"] == pytest.approx(10.0)
    assert day2["n"] == 1
    assert np.isnan(day2["sd"])


def test_daily_stats_empty_input():
    out = daily_stats(pd.DataFrame(columns=["metric", "start", "end", "value"]))
    assert out.empty
    assert list(out.columns) == ["metric", "date", "mean", "median", "sd", "n"]


def test_daily_stats_requires_tz_aware_start():
    rows = [_row("walking_speed_m_s", "2026-02-10", 1.0)]
    df = _frame(rows)
    df["start"] = df["start"].dt.tz_localize(None)
    with pytest.raises(ValueError, match="timezone-aware"):
        daily_stats(df)


def test_weekly_stats_groups_by_iso_week():
    # 2026-02-09 is a Monday; 2026-02-15 is the following Sunday (same ISO week).
    rows = [
        _row("step_length_m", "2026-02-09", 0.6),
        _row("step_length_m", "2026-02-15", 0.7),
        _row("step_length_m", "2026-02-16", 0.8),  # next week (Monday)
    ]
    out = weekly_stats(_frame(rows), local_tz=UTC)
    assert len(out) == 2
    first_week = out.iloc[0]
    assert first_week["week_start"] == date(2026, 2, 9)
    assert first_week["n"] == 2
    assert first_week["mean"] == pytest.approx(0.65)
    second_week = out.iloc[1]
    assert second_week["week_start"] == date(2026, 2, 16)
    assert second_week["n"] == 1


def test_local_tz_shifts_calendar_day():
    # 23:30 UTC on 2026-02-10, local Europe/Vienna (+01:00 in Feb) rolls it to 2026-02-11.
    row = _row("walking_speed_m_s", "2026-02-10", 1.0, hour=23)
    row["start"] = pd.Timestamp("2026-02-10 23:30:00", tz="UTC")
    out_utc = daily_stats(_frame([row]), local_tz="UTC")
    out_local = daily_stats(_frame([row]), local_tz="Europe/Vienna")
    assert out_utc.iloc[0]["date"] == date(2026, 2, 10)
    assert out_local.iloc[0]["date"] == date(2026, 2, 11)


# --- rolling_median_7d ---------------------------------------------------------------------


def test_rolling_median_7d_single_day_equals_daily_median():
    rows = [_row("walking_speed_m_s", "2026-02-10", 1.0)]
    out = rolling_median_7d(_frame(rows), local_tz=UTC)
    assert out.iloc[0]["rolling_median_7d"] == pytest.approx(out.iloc[0]["median"])


def test_rolling_median_7d_uses_trailing_window():
    # Daily medians 1..8 on consecutive days; on day 8 the trailing 7-day window is days 2-8
    # (medians 2..8), whose median is 5.
    rows = [_row("walking_speed_m_s", f"2026-02-{d:02d}", float(d)) for d in range(1, 9)]
    out = rolling_median_7d(_frame(rows), local_tz=UTC)
    last = out[out["date"] == date(2026, 2, 8)].iloc[0]
    assert last["rolling_median_7d"] == pytest.approx(5.0)


def test_rolling_median_7d_skips_gap_days():
    # Gap on day 3 must not be treated as zero: window over days 1,2,4,5 medians (skip missing).
    rows = [
        _row("walking_speed_m_s", "2026-02-01", 1.0),
        _row("walking_speed_m_s", "2026-02-02", 2.0),
        _row("walking_speed_m_s", "2026-02-04", 4.0),
    ]
    out = rolling_median_7d(_frame(rows), local_tz=UTC)
    on_day4 = out[out["date"] == date(2026, 2, 4)].iloc[0]
    assert on_day4["rolling_median_7d"] == pytest.approx(2.0)  # median of [1, 2, 4]


def test_rolling_median_7d_empty_input():
    out = rolling_median_7d(pd.DataFrame(columns=["metric", "start", "end", "value"]))
    assert out.empty
    assert "rolling_median_7d" in out.columns


# --- period_summary / period_summary_json ---------------------------------------------------


def test_period_summary_assigns_and_orders_periods():
    surgery = date(2026, 3, 1)
    rows = [
        _row("walking_speed_m_s", "2026-02-01", 1.2),  # vor OP
        _row("walking_speed_m_s", "2026-03-10", 0.8),  # 0-6 Wochen post-OP
        _row("walking_speed_m_s", "2026-09-01", 1.3),  # > 26 Wochen post-OP
    ]
    out = period_summary(_frame(rows), surgery, local_tz=UTC)
    assert list(out["period"].cat.categories) == list(PERIOD_ORDER)
    assert set(out["period"]) == {"vor OP", "0-6 Wochen post-OP", "> 26 Wochen post-OP"}
    vor_op = out[out["period"] == "vor OP"].iloc[0]
    assert vor_op["n"] == 1
    assert vor_op["mean"] == pytest.approx(1.2)


def test_period_summary_empty_input():
    out = period_summary(
        pd.DataFrame(columns=["metric", "start", "end", "value"]), date(2026, 3, 1)
    )
    assert out.empty


def test_period_summary_json_structure_and_note():
    surgery = date(2026, 3, 1)
    rows = [
        _row("double_support_pct", "2026-02-01", 20.0),
        _row("double_support_pct", "2026-03-10", 25.0),
    ]
    summary = period_summary_json(_frame(rows), surgery, local_tz=UTC)
    assert summary["surgery_date"] == "2026-03-01"
    assert summary["local_tz"] == UTC
    assert summary["period_order"] == list(PERIOD_ORDER)
    assert "double_support_pct" in summary["notes"]
    assert "ICC" in summary["notes"]["double_support_pct"]
    metrics = summary["metrics"]["double_support_pct"]
    assert metrics["vor OP"]["n"] == 1
    assert metrics["0-6 Wochen post-OP"]["mean"] == pytest.approx(25.0)

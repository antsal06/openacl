"""Daily/weekly aggregation of Apple Health gait metrics and ACLR recovery-period comparison.

Consumes the DataFrame produced by :func:`openacl.health.export.load_gait_export` (columns
``metric, start, end, value, unit, source_name, device``, ``start``/``end`` tz-aware UTC).

Known measurement property (documented here, not just in the README, so it travels with the
numbers): Apple's walking double-support percentage has an intraclass correlation of only
0.42-0.58 against a laboratory reference system (Sci Rep 2023;13, doi:10.1038/s41598-023-32550-3).
Consequence for everything in this module: outputs are day/week aggregates, a rolling median and
period comparisons -- trends, never a single record read as a clinical value. Downstream text
must stay in the "Beobachtung/Hypothese" register of ADR-0004, not "your double support is X %".

Local calendar day/week
------------------------
``start``/``end`` are stored as UTC instants (see ``export.py``). Bucketing by calendar day or
ISO week needs a local time zone; ``local_tz`` defaults to ``"Europe/Vienna"`` (Central European
Time, matches the offsets observed in this project's own export) and can be overridden.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Final

import numpy as np
import pandas as pd

DEFAULT_LOCAL_TZ: Final[str] = "Europe/Vienna"

DOUBLE_SUPPORT_ICC_NOTE: Final[str] = (
    "Doppelstuetz-Prozent aus Apple Health hat gegenueber einem Laborreferenzsystem nur eine "
    "ICC von 0,42-0,58 (Sci Rep 2023;13, doi:10.1038/s41598-023-32550-3). Einzelwerte sind "
    "damit nicht verlaesslich interpretierbar, nur Trends ueber Tage und Wochen."
)

#: Recovery periods relative to `surgery_date`, in this fixed display/sort order.
PERIOD_VOR_OP: Final[str] = "vor OP"
PERIOD_0_6: Final[str] = "0-6 Wochen post-OP"
PERIOD_6_12: Final[str] = "6-12 Wochen post-OP"
PERIOD_12_26: Final[str] = "12-26 Wochen post-OP"
PERIOD_26_PLUS: Final[str] = "> 26 Wochen post-OP"
PERIOD_ORDER: Final[tuple[str, ...]] = (
    PERIOD_VOR_OP,
    PERIOD_0_6,
    PERIOD_6_12,
    PERIOD_12_26,
    PERIOD_26_PLUS,
)


@dataclass(frozen=True)
class MetricStat:
    """Mean, median, standard deviation and record count of one metric over some period."""

    mean: float
    median: float
    sd: float
    n: int

    @classmethod
    def from_values(cls, values: Iterable[float]) -> MetricStat:
        v = np.asarray(list(values), dtype=float)
        v = v[np.isfinite(v)]
        if v.size == 0:
            return cls(float("nan"), float("nan"), float("nan"), 0)
        sd = float(np.std(v, ddof=1)) if v.size > 1 else float("nan")
        return cls(float(np.mean(v)), float(np.median(v)), sd, int(v.size))

    def to_dict(self) -> dict[str, float | int]:
        return {"mean": self.mean, "median": self.median, "sd": self.sd, "n": self.n}


def assign_period(day: date, surgery_date: date) -> str:
    """Map a calendar date to its ACLR recovery period relative to ``surgery_date``.

    Boundaries are whole weeks post-surgery: ``[0,6)``, ``[6,12)``, ``[12,26)``, ``[26, inf)``;
    anything before the surgery date is ``"vor OP"``.
    """
    weeks = (pd.Timestamp(day) - pd.Timestamp(surgery_date)).days / 7.0
    if weeks < 0:
        return PERIOD_VOR_OP
    if weeks < 6:
        return PERIOD_0_6
    if weeks < 12:
        return PERIOD_6_12
    if weeks < 26:
        return PERIOD_12_26
    return PERIOD_26_PLUS


def _empty_stat_frame(*extra_key_cols: str) -> pd.DataFrame:
    return pd.DataFrame(columns=["metric", *extra_key_cols, "mean", "median", "sd", "n"])


def _local_dates(df: pd.DataFrame, local_tz: str) -> pd.Series:
    start = df["start"]
    if start.dt.tz is None:
        raise ValueError("'start' must be timezone-aware (see openacl.health.export)")
    return start.dt.tz_convert(local_tz).dt.date


def daily_stats(df: pd.DataFrame, local_tz: str = DEFAULT_LOCAL_TZ) -> pd.DataFrame:
    """One row per ``(metric, local calendar day)``: mean, median, sd, n of that day's records."""
    if df.empty:
        return _empty_stat_frame("date")
    work = df.copy()
    work["date"] = _local_dates(work, local_tz)
    rows = [
        {"metric": metric, "date": day, **MetricStat.from_values(group["value"]).to_dict()}
        for (metric, day), group in work.groupby(["metric", "date"], sort=True)
    ]
    return pd.DataFrame(rows).sort_values(["metric", "date"]).reset_index(drop=True)


def weekly_stats(df: pd.DataFrame, local_tz: str = DEFAULT_LOCAL_TZ) -> pd.DataFrame:
    """One row per ``(metric, ISO week)``: mean, median, sd, n of that week's records.

    ``week_start`` is the Monday of the (local-time) ISO week.
    """
    if df.empty:
        return _empty_stat_frame("week_start")
    work = df.copy()
    local_naive = work["start"].dt.tz_convert(local_tz).dt.tz_localize(None)
    work["week_start"] = local_naive.dt.to_period("W-SUN").dt.start_time.dt.date
    rows = [
        {
            "metric": metric,
            "week_start": week_start,
            **MetricStat.from_values(group["value"]).to_dict(),
        }
        for (metric, week_start), group in work.groupby(["metric", "week_start"], sort=True)
    ]
    return pd.DataFrame(rows).sort_values(["metric", "week_start"]).reset_index(drop=True)


def rolling_median_7d(df: pd.DataFrame, local_tz: str = DEFAULT_LOCAL_TZ) -> pd.DataFrame:
    """:func:`daily_stats` with an added ``rolling_median_7d`` column.

    For metric ``m`` and day ``d``, ``rolling_median_7d`` is the median of the *daily medians*
    of ``m`` over the trailing 7 calendar days ``[d-6, d]`` (days with zero records are gaps,
    skipped rather than treated as zero) -- smoother than a single day, robust to the very
    uneven daily record counts a phone-worn sensor produces.
    """
    daily = daily_stats(df, local_tz=local_tz)
    if daily.empty:
        return daily.assign(rolling_median_7d=pd.Series(dtype=float))
    frames = []
    for metric, group in daily.groupby("metric", sort=True):
        g = group.set_index(pd.to_datetime(group["date"])).sort_index()
        g = g.asfreq("D")  # explicit gaps for missing days so the window spans real calendar time
        g["rolling_median_7d"] = g["median"].rolling(window=7, min_periods=1).median()
        g["metric"] = metric
        g["date"] = g.index.date
        frames.append(g.reset_index(drop=True))
    out = pd.concat(frames, ignore_index=True)
    return out[["metric", "date", "mean", "median", "sd", "n", "rolling_median_7d"]]


def period_summary(
    df: pd.DataFrame, surgery_date: date, local_tz: str = DEFAULT_LOCAL_TZ
) -> pd.DataFrame:
    """One row per ``(metric, recovery period)``: mean, median, sd, n of that period's records.

    Periods follow :data:`PERIOD_ORDER` relative to ``surgery_date`` (see :func:`assign_period`).
    """
    if df.empty:
        out = _empty_stat_frame("period")
        out["period"] = pd.Categorical(out["period"], categories=PERIOD_ORDER, ordered=True)
        return out
    work = df.copy()
    local_dates = _local_dates(work, local_tz)
    work["period"] = [assign_period(day, surgery_date) for day in local_dates]
    rows = [
        {"metric": metric, "period": period, **MetricStat.from_values(group["value"]).to_dict()}
        for (metric, period), group in work.groupby(["metric", "period"], sort=False)
    ]
    out = pd.DataFrame(rows)
    out["period"] = pd.Categorical(out["period"], categories=PERIOD_ORDER, ordered=True)
    return out.sort_values(["metric", "period"]).reset_index(drop=True)


def period_summary_json(
    df: pd.DataFrame, surgery_date: date, local_tz: str = DEFAULT_LOCAL_TZ
) -> dict[str, object]:
    """Nest :func:`period_summary` into a JSON-serializable ``{metric: {period: stats}}`` dict.

    Includes ``surgery_date``, ``local_tz`` and :data:`DOUBLE_SUPPORT_ICC_NOTE` so the
    measurement-quality caveat travels with the numbers into ``health_summary.json``.
    """
    summary = period_summary(df, surgery_date, local_tz=local_tz)
    by_metric: dict[str, dict[str, dict[str, float | int]]] = {}
    for row in summary.itertuples(index=False):
        by_metric.setdefault(row.metric, {})[str(row.period)] = {
            "mean": row.mean,
            "median": row.median,
            "sd": row.sd,
            "n": row.n,
        }
    return {
        "surgery_date": surgery_date.isoformat(),
        "local_tz": local_tz,
        "period_order": list(PERIOD_ORDER),
        "metrics": by_metric,
        "notes": {"double_support_pct": DOUBLE_SUPPORT_ICC_NOTE},
    }

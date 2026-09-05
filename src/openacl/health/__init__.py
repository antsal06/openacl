"""Apple Health export as a second gait-metric data source (ADR-0005, "Sensor-Track").

Not wired into ``openacl.cli`` yet; use ``python -m openacl.health`` or import the submodules
directly. See ``src/openacl/health/README.md`` for what these metrics are (and are not).
"""

from __future__ import annotations

from .daily import (
    DEFAULT_LOCAL_TZ,
    DOUBLE_SUPPORT_ICC_NOTE,
    PERIOD_ORDER,
    MetricStat,
    assign_period,
    daily_stats,
    period_summary,
    period_summary_json,
    rolling_median_7d,
    weekly_stats,
)
from .export import GAIT_RECORD_TYPES, load_gait_export

__all__ = [
    "DEFAULT_LOCAL_TZ",
    "DOUBLE_SUPPORT_ICC_NOTE",
    "GAIT_RECORD_TYPES",
    "PERIOD_ORDER",
    "MetricStat",
    "assign_period",
    "daily_stats",
    "load_gait_export",
    "period_summary",
    "period_summary_json",
    "rolling_median_7d",
    "weekly_stats",
]

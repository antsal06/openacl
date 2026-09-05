"""Four-panel trend plot of the Apple Health gait metrics (speed, step length, double support,
asymmetry) over time, with the surgery date and ACLR recovery periods marked.

Wording is kept neutral (ADR-0004): the figure shows observations, not a diagnosis or a
"good/bad" judgement, and carries the double-support measurement-quality caveat (see
``openacl.health.daily.DOUBLE_SUPPORT_ICC_NOTE``) as a footer note.

Colors follow the project's sequential single-hue convention: one blue hue for the (single)
data series per panel, muted grays for chrome/shading, no traffic-light colors.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Final

import pandas as pd

from .daily import PERIOD_ORDER

# Colors (light-mode reference palette; see the dataviz skill's palette.md).
_SURFACE = "#fcfcfb"
_PRIMARY_INK = "#0b0b0b"
_SECONDARY_INK = "#52514e"
_MUTED_INK = "#898781"
_GRIDLINE = "#e1e0d9"
_BAND_FILL = "#f0efec"
_BLUE_LINE = "#2a78d6"
_BLUE_DOT = "#86b6ef"

_PANELS: Final[tuple[tuple[str, str], ...]] = (
    ("walking_speed_m_s", "Gehgeschwindigkeit (m/s)"),
    ("step_length_m", "Schrittlänge (m)"),
    ("double_support_pct", "Doppelstützzeit (%)"),
    ("walking_asymmetry_pct", "Gehasymmetrie (%)"),
)

_FOOTER = (
    "Beobachtung, keine Diagnose oder Therapieempfehlung (ADR-0004). Punkte = Tagesmedian, "
    "Linie = gleitender 7-Tage-Median. Graue Flächen = Reha-Perioden in Wochen post-OP "
    "(vor OP / 0–6 / 6–12 / 12–26 / >26). Doppelstütz hat gegenüber einem Laborreferenzsystem "
    "nur eine ICC von 0,42–0,58 (Sci Rep 2023;13, doi:10.1038/s41598-023-32550-3) – als Trend "
    "brauchbar, Einzelwerte nicht überinterpretieren."
)

#: Short on-chart labels for the (long, JSON-facing) period names in PERIOD_ORDER.
_SHORT_BAND_LABEL: Final[dict[str, str]] = {
    "vor OP": "vor OP",
    "0-6 Wochen post-OP": "0–6",
    "6-12 Wochen post-OP": "6–12",
    "12-26 Wochen post-OP": "12–26",
    "> 26 Wochen post-OP": ">26",
}

#: Skip an on-chart band label if it would occupy less than this fraction of the x-axis
#: (still shaded, just unlabeled) -- avoids overlapping text when a period is a thin sliver
#: of a much longer overall time range.
_MIN_LABEL_FRACTION = 0.035


def _period_bands(
    surgery_date: date, data_min: date, data_max: date
) -> list[tuple[date, date, str]]:
    """Clip the fixed ACLR recovery-period boundaries to the plotted date range."""
    edges = [
        data_min,
        surgery_date,
        surgery_date + timedelta(weeks=6),
        surgery_date + timedelta(weeks=12),
        surgery_date + timedelta(weeks=26),
        data_max,
    ]
    clipped = [max(data_min, min(edge, data_max)) for edge in edges]
    bands = list(zip(clipped[:-1], clipped[1:], PERIOD_ORDER, strict=True))
    return [(start, end, label) for start, end, label in bands if end > start]


def plot_trends(daily_df: pd.DataFrame, out_path: Path, surgery_date: date | None = None) -> None:
    """Write a 4-panel PNG (speed, step length, double support, asymmetry) to ``out_path``.

    ``daily_df`` is the output of :func:`openacl.health.daily.rolling_median_7d` (columns
    ``metric, date, mean, median, sd, n, rolling_median_7d``). Panels for metrics with no
    records are drawn empty with a note rather than omitted, so the figure always has 4 panels.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_path = Path(out_path)
    fig, axes = plt.subplots(len(_PANELS), 1, sharex=True, figsize=(11, 10), facecolor=_SURFACE)

    non_empty = daily_df[daily_df["n"] > 0] if not daily_df.empty else daily_df
    data_min = pd.to_datetime(non_empty["date"]).min() if not non_empty.empty else None
    data_max = pd.to_datetime(non_empty["date"]).max() if not non_empty.empty else None
    bands: list[tuple[date, date, str]] = []
    total_days = 1.0
    if surgery_date is not None and data_min is not None and data_max is not None:
        bands = _period_bands(surgery_date, data_min.date(), data_max.date())
        total_days = max((data_max.date() - data_min.date()).days, 1)

    for panel_i, (ax, (metric, title)) in enumerate(zip(axes, _PANELS, strict=True)):
        ax.set_facecolor(_SURFACE)
        ax.set_title(title, loc="left", color=_PRIMARY_INK, fontsize=11)
        ax.grid(True, color=_GRIDLINE, linewidth=0.8)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color(_MUTED_INK)
        ax.tick_params(colors=_MUTED_INK, labelsize=9)

        for start, end, label in bands:
            ax.axvspan(start, end, color=_BAND_FILL, zorder=0, linewidth=0)
            if panel_i == 0 and (end - start).days / total_days >= _MIN_LABEL_FRACTION:
                mid = start + (end - start) / 2
                ax.text(
                    mid,
                    1.02,
                    _SHORT_BAND_LABEL[label],
                    transform=ax.get_xaxis_transform(),
                    ha="center",
                    va="bottom",
                    fontsize=7,
                    color=_MUTED_INK,
                    clip_on=False,
                )

        sub = daily_df[daily_df["metric"] == metric] if not daily_df.empty else daily_df
        sub = sub[sub["n"] > 0] if not sub.empty else sub
        if sub.empty:
            ax.text(
                0.5,
                0.5,
                "keine Daten",
                transform=ax.transAxes,
                ha="center",
                va="center",
                color=_MUTED_INK,
                fontsize=9,
            )
        else:
            dates = pd.to_datetime(sub["date"])
            ax.scatter(
                dates,
                sub["median"],
                s=10,
                color=_BLUE_DOT,
                alpha=0.6,
                linewidths=0,
                label="Tagesmedian",
                zorder=2,
            )
            ax.plot(
                dates,
                sub["rolling_median_7d"],
                color=_BLUE_LINE,
                linewidth=2,
                label="7-Tage-Median",
                zorder=3,
            )

        if surgery_date is not None:
            ax.axvline(surgery_date, color=_SECONDARY_INK, linestyle="--", linewidth=1.2, zorder=1)
            if panel_i == 0:
                ax.text(
                    surgery_date,
                    1.10,
                    "OP",
                    transform=ax.get_xaxis_transform(),
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color=_SECONDARY_INK,
                    clip_on=False,
                )

    handles, labels = axes[0].get_legend_handles_labels()
    if handles:
        fig.legend(
            handles,
            labels,
            loc="upper right",
            ncol=2,
            fontsize=9,
            frameon=False,
            labelcolor=_SECONDARY_INK,
        )

    fig.suptitle("Apple-Health-Gangmetriken im Verlauf", color=_PRIMARY_INK, fontsize=13, y=0.995)
    fig.text(0.01, 0.005, _FOOTER, fontsize=7, color=_MUTED_INK, wrap=True, va="bottom")
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    fig.savefig(out_path, dpi=150, facecolor=_SURFACE)
    plt.close(fig)

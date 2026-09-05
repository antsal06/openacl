"""Minimal Detectable Change (MDC) from repeated measurements.

Formulas
--------
Intraclass correlation ICC(2,1) (two-way random effects, absolute agreement, single
measurement), Shrout PE & Fleiss JL (1979), "Intraclass correlations: uses in assessing rater
reliability", *Psychol Bull* 86(2):420-428::

    ICC(2,1) = (MS_R - MS_E) / (MS_R + (k-1) * MS_E + k * (MS_C - MS_E) / n)

with ``n`` rows (measurement targets: subjects, trials or cycles), ``k`` columns (repeated
sessions), ``MS_R`` between-row, ``MS_C`` between-column and ``MS_E`` residual mean square.

Standard error of measurement and minimal detectable change at 95 % confidence
(Weir JP 2005, *J Strength Cond Res* 19(1):231-240)::

    SEM   = SD_pooled * sqrt(1 - ICC)
    MDC95 = 1.96 * sqrt(2) * SEM

``SD_pooled`` is the standard deviation of all observations (ddof=1).

Rationale (ADR-0003): nothing is flagged that lies below the MDC. The effect sizes of interest
after ACL reconstruction (~2.6 deg peak knee flexion difference, Sajedi 2025) are smaller than
the measurement error of a single smartphone recording, so the MDC is a hard gate, not decoration.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

Z_95 = 1.959964
MDC_FACTOR = Z_95 * np.sqrt(2.0)


@dataclass(frozen=True)
class ReliabilityResult:
    """ICC, SEM and MDC95 of one parameter from a repeated-measurement design."""

    icc_2_1: float
    sem: float
    mdc95: float
    sd_pooled: float
    n_targets: int
    n_sessions: int
    unit: str = ""
    source: str = "Shrout & Fleiss 1979; Weir 2005, J Strength Cond Res 19:231-240"


@dataclass(frozen=True)
class LiteratureMdc:
    """A default MDC taken from the literature, used until own repeat measurements exist."""

    value: float
    unit: str
    source: str
    placeholder: bool = False
    note: str = ""


DEFAULT_MDC: dict[str, LiteratureMdc] = {
    "peak_knee_flexion_deg": LiteratureMdc(
        value=9.2,
        unit="deg",
        source="Gait & Posture 2017, PMID 28288331 (ICC 0.86, marker-based lab)",
    ),
    "sagittal_joint_angle_deg": LiteratureMdc(
        value=7.5,
        unit="deg",
        source="pooled reliability studies, MDC range 3.8-11.5 deg (see docs/research/02)",
        note="generic fallback for sagittal joint angles without a specific value",
    ),
    "stance_pct": LiteratureMdc(
        value=5.0,
        unit="pct",
        source="conservative assumption, no published video-based value",
        placeholder=True,
        note="placeholder, replace with own repeat measurements",
    ),
    "swing_pct": LiteratureMdc(
        value=5.0,
        unit="pct",
        source="conservative assumption, no published video-based value",
        placeholder=True,
        note="placeholder, replace with own repeat measurements",
    ),
    "double_support_pct": LiteratureMdc(
        value=5.0,
        unit="pct",
        source="conservative assumption, no published video-based value",
        placeholder=True,
        note="placeholder, replace with own repeat measurements",
    ),
    "stride_time_s": LiteratureMdc(
        value=0.05,
        unit="s",
        source="conservative assumption, no published video-based value",
        placeholder=True,
        note="placeholder, replace with own repeat measurements",
    ),
    "walking_speed_m_s": LiteratureMdc(
        value=0.10,
        unit="m/s",
        source="conservative assumption, no published video-based value",
        placeholder=True,
        note="placeholder, replace with own repeat measurements",
    ),
}
"""Literature fallbacks. Every entry carries its source; placeholders are marked as such."""


def icc_2_1(values: np.ndarray) -> float:
    """ICC(2,1) after Shrout & Fleiss 1979 for a ``(n_targets, n_sessions)`` matrix."""
    x = np.asarray(values, dtype=float)
    if x.ndim != 2:
        raise ValueError(f"expected a 2-D (targets x sessions) matrix, got shape {x.shape}")
    if not np.isfinite(x).all():
        raise ValueError("ICC needs a complete matrix without NaN")
    n, k = x.shape
    if n < 2 or k < 2:
        raise ValueError(f"need at least 2 targets and 2 sessions, got {n} x {k}")

    grand = x.mean()
    ss_rows = k * float(((x.mean(axis=1) - grand) ** 2).sum())
    ss_cols = n * float(((x.mean(axis=0) - grand) ** 2).sum())
    ss_total = float(((x - grand) ** 2).sum())
    ss_error = ss_total - ss_rows - ss_cols

    ms_rows = ss_rows / (n - 1)
    ms_cols = ss_cols / (k - 1)
    ms_error = ss_error / ((n - 1) * (k - 1))

    denominator = ms_rows + (k - 1) * ms_error + k * (ms_cols - ms_error) / n
    if denominator == 0:
        return float("nan")
    return float((ms_rows - ms_error) / denominator)


def reliability_from_repeats(values: np.ndarray, unit: str = "") -> ReliabilityResult:
    """ICC(2,1), SEM and MDC95 from a ``(n_targets, n_sessions)`` matrix of one parameter."""
    x = np.asarray(values, dtype=float)
    icc = icc_2_1(x)
    sd_pooled = float(np.std(x, ddof=1))
    icc_clipped = min(max(icc, 0.0), 1.0)  # a negative ICC is treated as zero reliability
    sem = sd_pooled * float(np.sqrt(1.0 - icc_clipped))
    return ReliabilityResult(
        icc_2_1=icc,
        sem=sem,
        mdc95=float(MDC_FACTOR * sem),
        sd_pooled=sd_pooled,
        n_targets=int(x.shape[0]),
        n_sessions=int(x.shape[1]),
        unit=unit,
    )


def mdc_table_from_sessions(
    sessions: Mapping[str, np.ndarray] | np.ndarray,
    parameter_names: list[str] | None = None,
) -> dict[str, ReliabilityResult]:
    """Compute reliability for several parameters at once.

    Accepts either a mapping ``parameter -> (n_targets, n_sessions)`` matrix, or a 3-D array
    ``(n_sessions, n_targets, n_parameters)`` together with ``parameter_names``.
    """
    if isinstance(sessions, Mapping):
        return {name: reliability_from_repeats(matrix) for name, matrix in sessions.items()}
    arr = np.asarray(sessions, dtype=float)
    if arr.ndim != 3:
        raise ValueError(f"expected a 3-D (sessions x targets x parameters) array, got {arr.shape}")
    if parameter_names is None or len(parameter_names) != arr.shape[2]:
        raise ValueError("parameter_names must match the last axis of the array")
    return {
        name: reliability_from_repeats(arr[:, :, j].T) for j, name in enumerate(parameter_names)
    }


def is_above_mdc(delta: float, mdc: float) -> bool:
    """``True`` when a change exceeds the minimal detectable change (absolute value)."""
    d, m = float(delta), float(mdc)
    if not (np.isfinite(d) and np.isfinite(m)):
        return False
    return abs(d) > abs(m)


def default_mdc(parameter: str) -> LiteratureMdc | None:
    """Literature fallback MDC for ``parameter``, or ``None`` if none is defined."""
    return DEFAULT_MDC.get(parameter)

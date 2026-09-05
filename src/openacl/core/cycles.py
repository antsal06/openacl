"""Gait cycle segmentation and time normalisation to 0-100 % of the cycle.

One cycle runs from one heel strike to the next heel strike of the *same* side (stride).
Every angle channel is resampled onto ``n_points`` (default 101) evenly spaced phase values,
which is the standard representation for norm bands and curve comparison
(Baker et al. 2009, *Gait Posture* 30:265-269; Perry & Burnfield, *Gait Analysis*).

Cycles are flagged invalid when
- the stride duration is implausible (outside ``min/max_stride_time_s``),
- the stride duration deviates more than ``outlier_sd`` standard deviations from the median,
- more than ``max_nan_pct`` percent of the samples of a channel are missing.
"""

from __future__ import annotations

import warnings as _warnings
from dataclasses import dataclass, field

import numpy as np

from openacl.schema import KinematicsResult, Side

from .events import SIDES, GaitEvents

N_POINTS = 101
MIN_STRIDE_TIME_S = 0.6
MAX_STRIDE_TIME_S = 4.0
OUTLIER_SD = 2.0
MAX_NAN_PCT = 20.0
MIN_DURATION_SD_S = 0.005
"""Below this stride-time SD the outlier rule is switched off (numerically too regular)."""


def _base_channel(name: str) -> tuple[str, Side | None]:
    """Split ``"knee_flexion_deg_L"`` into ``("knee_flexion_deg", "L")``."""
    if name.endswith("_L"):
        return name[:-2], "L"
    if name.endswith("_R"):
        return name[:-2], "R"
    return name, None


@dataclass(frozen=True, eq=False)
class CycleMeta:
    """Metadata of a single stride."""

    side: Side
    index: int
    start_frame: int
    end_frame: int
    start_time_s: float
    duration_s: float
    nan_pct: float
    valid: bool
    reason: str = ""


@dataclass(eq=False)
class GaitCycles:
    """Time-normalised angle curves per side, plus per-cycle metadata."""

    phase_pct: np.ndarray
    """Shape ``(n_points,)``, 0 .. 100."""
    curves: dict[Side, dict[str, np.ndarray]]
    """``curves["L"]["knee_flexion_deg"]`` has shape ``(n_cycles_L, n_points)``."""
    meta: dict[Side, list[CycleMeta]]
    warnings: tuple[str, ...] = ()
    info: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ helpers
    @property
    def n_points(self) -> int:
        return int(self.phase_pct.size)

    def channels(self, side: Side) -> tuple[str, ...]:
        return tuple(sorted(self.curves.get(side, {})))

    def valid_mask(self, side: Side) -> np.ndarray:
        return np.array([m.valid for m in self.meta.get(side, [])], dtype=bool)

    def n_valid(self, side: Side) -> int:
        return int(self.valid_mask(side).sum())

    def cycle_array(self, channel: str, side: Side, only_valid: bool = True) -> np.ndarray | None:
        """Return ``(n_cycles, n_points)`` for ``channel`` (with or without side suffix)."""
        base, suffix = _base_channel(channel)
        if suffix is not None and suffix != side:
            return None
        arr = self.curves.get(side, {}).get(base)
        if arr is None or arr.size == 0:
            return None
        if only_valid:
            mask = self.valid_mask(side)
            if mask.size == arr.shape[0]:
                arr = arr[mask]
        return arr if arr.shape[0] else None

    def mean_curve_deg(
        self, channel: str, side: Side, only_valid: bool = True
    ) -> np.ndarray | None:
        """Mean curve over cycles, ignoring NaN. ``None`` if the channel is absent."""
        arr = self.cycle_array(channel, side, only_valid=only_valid)
        if arr is None:
            return None
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore", RuntimeWarning)
            return np.nanmean(arr, axis=0)

    def sd_curve_deg(self, channel: str, side: Side, only_valid: bool = True) -> np.ndarray | None:
        arr = self.cycle_array(channel, side, only_valid=only_valid)
        if arr is None or arr.shape[0] < 2:
            return None
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore", RuntimeWarning)
            return np.nanstd(arr, axis=0, ddof=1)


def _resample_cycle(y: np.ndarray, start: int, end: int, n_points: int) -> tuple[np.ndarray, float]:
    """Resample ``y[start:end+1]`` onto ``n_points`` phase samples. Returns curve and NaN share."""
    window = y[start : end + 1]
    n = window.size
    if n < 2:
        return np.full(n_points, np.nan), 100.0
    source_pct = np.linspace(0.0, 100.0, n)
    target_pct = np.linspace(0.0, 100.0, n_points)
    finite = np.isfinite(window)
    nan_pct = 100.0 * float(np.mean(~finite))
    if finite.sum() < 2:
        return np.full(n_points, np.nan), nan_pct
    out = np.interp(target_pct, source_pct[finite], window[finite])
    # Do not invent data across long gaps: blank out targets far from any observed sample.
    if nan_pct > 0:
        gap_pct = 100.0 / max(1, n - 1)
        observed = source_pct[finite]
        nearest = np.abs(target_pct[:, None] - observed[None, :]).min(axis=1)
        out[nearest > 2.0 * gap_pct] = np.nan
    return out, nan_pct


def normalize_cycles(
    result: KinematicsResult,
    events: GaitEvents,
    *,
    n_points: int = N_POINTS,
    min_stride_time_s: float = MIN_STRIDE_TIME_S,
    max_stride_time_s: float = MAX_STRIDE_TIME_S,
    outlier_sd: float = OUTLIER_SD,
    max_nan_pct: float = MAX_NAN_PCT,
) -> GaitCycles:
    """Cut ``result`` into strides and time-normalise every angle channel to 0-100 %."""
    time_s = np.asarray(result.time_s, dtype=float)
    phase_pct = np.linspace(0.0, 100.0, n_points)
    curves: dict[Side, dict[str, np.ndarray]] = {s: {} for s in SIDES}
    meta: dict[Side, list[CycleMeta]] = {s: [] for s in SIDES}
    warnings: list[str] = []

    for side in SIDES:
        hs = events.heel_strikes(side)
        if hs.size < 2:
            continue
        starts, ends = hs[:-1], hs[1:]
        durations_s = time_s[ends] - time_s[starts]

        channels: dict[str, np.ndarray] = {}
        for name, series in result.angles_deg.items():
            base, suffix = _base_channel(name)
            if suffix is not None and suffix != side:
                continue  # channel belongs to the other side
            channels[base] = np.asarray(series, dtype=float)

        per_channel: dict[str, list[np.ndarray]] = {c: [] for c in channels}
        nan_pct_per_cycle = np.zeros(starts.size)
        for k, (start, end) in enumerate(zip(starts, ends, strict=True)):
            worst_nan_pct = 0.0
            for name, series in channels.items():
                curve, nan_pct = _resample_cycle(series, int(start), int(end), n_points)
                per_channel[name].append(curve)
                worst_nan_pct = max(worst_nan_pct, nan_pct)
            nan_pct_per_cycle[k] = worst_nan_pct

        median_s = float(np.median(durations_s))
        sd_s = float(np.std(durations_s, ddof=1)) if durations_s.size > 2 else 0.0
        if sd_s < MIN_DURATION_SD_S:
            sd_s = 0.0  # do not flag outliers on numerical noise of a very regular gait
        for k, (start, end) in enumerate(zip(starts, ends, strict=True)):
            duration_s = float(durations_s[k])
            reasons: list[str] = []
            if not (min_stride_time_s <= duration_s <= max_stride_time_s):
                reasons.append(f"implausible stride duration {duration_s:.2f} s")
            if sd_s > 0 and abs(duration_s - median_s) > outlier_sd * sd_s:
                reasons.append(
                    f"stride duration {duration_s:.2f} s deviates > {outlier_sd:g} SD "
                    f"from the median ({median_s:.2f} s)"
                )
            if nan_pct_per_cycle[k] > max_nan_pct:
                reasons.append(f"{nan_pct_per_cycle[k]:.0f} % missing samples")
            meta[side].append(
                CycleMeta(
                    side=side,
                    index=k,
                    start_frame=int(start),
                    end_frame=int(end),
                    start_time_s=float(time_s[start]),
                    duration_s=duration_s,
                    nan_pct=float(nan_pct_per_cycle[k]),
                    valid=not reasons,
                    reason="; ".join(reasons),
                )
            )
        curves[side] = {name: np.asarray(rows, dtype=float) for name, rows in per_channel.items()}
        if not curves[side]:
            warnings.append(f"no angle channel available for side {side}")

    return GaitCycles(
        phase_pct=phase_pct,
        curves=curves,
        meta=meta,
        warnings=tuple(warnings),
        info={"n_points": n_points, "definition": "heel strike to ipsilateral heel strike"},
    )

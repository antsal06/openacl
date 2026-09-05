"""Spatio-temporal gait parameters per side, per stride, and pooled over both sides.

Definitions follow the standard gait-cycle terminology (Perry & Burnfield, *Gait Analysis:
Normal and Pathological Function*, 2nd ed.; Kadaba et al. 1990, *J Orthop Res* 8:383-392):

- stride (gait cycle): heel strike to ipsilateral heel strike
- step: contralateral heel strike to ipsilateral heel strike
- stance: heel strike to ipsilateral toe off; swing: the remainder of the stride
- double support: both feet on the ground; initial (HS to contralateral TO) plus
  terminal (contralateral HS to ipsilateral TO) double support, expressed as % of the stride
- cadence: 120 / stride time (two steps per stride), in steps per minute

Reference values in healthy adults for orientation (docs/research/02, section 4):
stance ~60 %, total double support ~20-24 %, cadence ~100-120 steps/min,
walking speed ~1.2-1.4 m/s, step length ~0.65-0.75 m.

Spatial parameters are only computed when ``KinematicsResult.keypoint_unit == "m"``; for
pixel keypoints they are ``None`` because no scale is known.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

import numpy as np

from openacl.schema import KinematicsResult, Side, sided

from .events import SIDES, GaitEvents

TEMPORAL_PARAMS: tuple[str, ...] = (
    "stride_time_s",
    "step_time_s",
    "stance_time_s",
    "swing_time_s",
    "stance_pct",
    "swing_pct",
    "double_support_pct",
    "cadence_steps_per_min",
)
SPATIAL_PARAMS: tuple[str, ...] = ("step_length_m", "stride_length_m", "walking_speed_m_s")
ALL_PARAMS: tuple[str, ...] = TEMPORAL_PARAMS + SPATIAL_PARAMS


@dataclass(frozen=True)
class ParamStat:
    """Mean, standard deviation and number of contributing cycles of one parameter."""

    mean: float
    sd: float
    n: int

    @classmethod
    def from_values(cls, values: Iterable[float]) -> ParamStat:
        v = np.asarray(list(values), dtype=float)
        v = v[np.isfinite(v)]
        if v.size == 0:
            return cls(float("nan"), float("nan"), 0)
        sd = float(np.std(v, ddof=1)) if v.size > 1 else float("nan")
        return cls(float(np.mean(v)), sd, int(v.size))

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return f"{self.mean:.3g} ± {self.sd:.3g} (n={self.n})"


@dataclass(eq=False)
class SideSpatiotemporal:
    """All spatio-temporal parameters of one side (or pooled over both)."""

    side: Side | None
    stride_time_s: ParamStat
    step_time_s: ParamStat
    stance_time_s: ParamStat
    swing_time_s: ParamStat
    stance_pct: ParamStat
    swing_pct: ParamStat
    double_support_pct: ParamStat
    cadence_steps_per_min: ParamStat
    step_length_m: ParamStat | None = None
    stride_length_m: ParamStat | None = None
    walking_speed_m_s: ParamStat | None = None

    def get(self, name: str) -> ParamStat | None:
        return getattr(self, name)

    def as_dict(self) -> dict[str, ParamStat | None]:
        return {name: getattr(self, name) for name in ALL_PARAMS}


@dataclass(eq=False)
class Spatiotemporal:
    """Per-side and pooled spatio-temporal parameters plus the raw per-stride values."""

    L: SideSpatiotemporal
    R: SideSpatiotemporal
    both: SideSpatiotemporal
    keypoint_unit: str
    per_stride: dict[Side, dict[str, np.ndarray]] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def side(self, side: Side | None) -> SideSpatiotemporal:
        if side is None:
            return self.both
        return self.L if side == "L" else self.R

    @property
    def has_spatial(self) -> bool:
        return self.both.walking_speed_m_s is not None


def _next_after(events: np.ndarray, frame: int, limit: int) -> int | None:
    """First event strictly after ``frame`` and strictly before ``limit``."""
    hits = events[(events > frame) & (events < limit)]
    return int(hits[0]) if hits.size else None


def _prev_before(events: np.ndarray, frame: int, limit: int) -> int | None:
    """Last event strictly before ``frame`` and at or after ``limit``."""
    hits = events[(events < frame) & (events >= limit)]
    return int(hits[-1]) if hits.size else None


def _stride_values(
    result: KinematicsResult,
    events: GaitEvents,
    side: Side,
    valid_mask: np.ndarray | None,
) -> dict[str, np.ndarray]:
    """Per-stride raw values for one side; NaN where an event is missing."""
    other: Side = "R" if side == "L" else "L"
    time_s = np.asarray(result.time_s, dtype=float)
    hs = events.heel_strikes(side)
    hs_other = events.heel_strikes(other)
    to = events.toe_offs(side)
    to_other = events.toe_offs(other)
    spatial = result.keypoint_unit == "m"
    heel_key, heel_key_other = sided("heel", side), sided("heel", other)
    if spatial and (heel_key not in result.keypoints or heel_key_other not in result.keypoints):
        spatial = False
    sign = float(events.direction_sign)

    def heel_x(key: str, frame: int) -> float:
        return sign * float(result.keypoints[key][frame, 0])

    n = max(0, hs.size - 1)
    out = {name: np.full(n, np.nan) for name in ALL_PARAMS}
    for k in range(n):
        if valid_mask is not None and valid_mask.size == n and not valid_mask[k]:
            continue
        start, end = int(hs[k]), int(hs[k + 1])
        stride_time_s = float(time_s[end] - time_s[start])
        if stride_time_s <= 0:
            continue
        out["stride_time_s"][k] = stride_time_s
        out["cadence_steps_per_min"][k] = 120.0 / stride_time_s

        to_ipsi = _next_after(to, start, end)
        hs_contra = _next_after(hs_other, start, end)
        to_contra = _next_after(to_other, start, end)
        hs_contra_prev = _prev_before(hs_other, start, 0)

        if to_ipsi is not None:
            stance_time_s = float(time_s[to_ipsi] - time_s[start])
            out["stance_time_s"][k] = stance_time_s
            out["swing_time_s"][k] = stride_time_s - stance_time_s
            out["stance_pct"][k] = 100.0 * stance_time_s / stride_time_s
            out["swing_pct"][k] = 100.0 - out["stance_pct"][k]
        if hs_contra_prev is not None:
            out["step_time_s"][k] = float(time_s[start] - time_s[hs_contra_prev])
        if hs_contra is not None and to_contra is not None and to_ipsi is not None:
            to_after_contra = _next_after(to, hs_contra, end + 1)
            initial_ds_s = float(time_s[to_contra] - time_s[start])
            terminal_ds_s = (
                float(time_s[to_after_contra] - time_s[hs_contra])
                if to_after_contra is not None
                else float("nan")
            )
            if initial_ds_s >= 0 and np.isfinite(terminal_ds_s) and terminal_ds_s >= 0:
                out["double_support_pct"][k] = (
                    100.0 * (initial_ds_s + terminal_ds_s) / stride_time_s
                )
        if spatial:
            stride_length_m = heel_x(heel_key, end) - heel_x(heel_key, start)
            out["stride_length_m"][k] = stride_length_m
            out["walking_speed_m_s"][k] = stride_length_m / stride_time_s
            if hs_contra_prev is not None:
                out["step_length_m"][k] = heel_x(heel_key, start) - heel_x(
                    heel_key_other, hs_contra_prev
                )
    if not spatial:
        for name in SPATIAL_PARAMS:
            out[name] = np.full(n, np.nan)
    return out


def _build(
    side: Side | None, values: Mapping[str, np.ndarray], spatial: bool
) -> SideSpatiotemporal:
    stats = {name: ParamStat.from_values(values[name]) for name in ALL_PARAMS}
    if not spatial:
        for name in SPATIAL_PARAMS:
            stats[name] = None  # type: ignore[assignment]
    return SideSpatiotemporal(side=side, **stats)  # type: ignore[arg-type]


def compute_spatiotemporal(
    result: KinematicsResult,
    events: GaitEvents,
    *,
    valid_masks: Mapping[Side, np.ndarray] | None = None,
) -> Spatiotemporal:
    """Compute spatio-temporal parameters per side and pooled over both sides.

    ``valid_masks`` (optional, from :class:`openacl.core.cycles.GaitCycles`) excludes
    outlier strides from the statistics.
    """
    per_stride: dict[Side, dict[str, np.ndarray]] = {}
    for side in SIDES:
        mask = None if valid_masks is None else np.asarray(valid_masks.get(side, []), dtype=bool)
        per_stride[side] = _stride_values(result, events, side, mask)

    spatial = (
        result.keypoint_unit == "m"
        and np.isfinite(np.concatenate([per_stride[s]["walking_speed_m_s"] for s in SIDES])).any()
    )
    pooled = {name: np.concatenate([per_stride[s][name] for s in SIDES]) for name in ALL_PARAMS}
    warnings: list[str] = []
    if result.keypoint_unit != "m":
        warnings.append(
            "keypoint_unit is 'px': step length, stride length and walking speed are not "
            "computable without a scale"
        )
    return Spatiotemporal(
        L=_build("L", per_stride["L"], spatial),
        R=_build("R", per_stride["R"], spatial),
        both=_build(None, pooled, spatial),
        keypoint_unit=result.keypoint_unit,
        per_stride=per_stride,
        warnings=tuple(warnings),
    )

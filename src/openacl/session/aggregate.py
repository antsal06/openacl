"""Pool all valid gait cycles of a session and derive the session key figures (ADR-0009).

Pooling
-------
Gait-core produces one :class:`~openacl.core.pipeline.GaitAnalysis` per pass. This module takes
the *valid* cycles of every pass and pools them per side. By default only the camera-near side
of each pass contributes (``pooling="camera_near"``), because the camera-far leg is partly
occluded in a sagittal video and its keypoints are markedly less reliable; the alternating
walking directions of the protocol give roughly the same number of cycles per side anyway.
``pooling="all_sides"`` keeps both legs of every pass.

Key figures per side: mean, SD, number of contributing cycles and the 95 % confidence interval
of the mean from the t distribution (``mean +- t(0.975, n-1) * sd / sqrt(n)``). The CI describes
the precision of the session mean, not the spread of the cycles -- both are reported.

Symmetry
--------
Robinson's Symmetry Index re-signed so that **positive means the operated side is larger**
(:func:`symmetry_index_operated_pct`), plus Plotnik's Gait Asymmetry on the swing times.

Norm comparison
---------------
Gait Variable Score per channel and Gait Profile Score per side (Baker et al. 2009) against
the speed-classified norm bands. The speed class comes from the Froude number of the measured
walking speed; without a metric scale it falls back to ``"comfortable"`` with a warning.

Flags
-----
A side difference is only flagged when its absolute value exceeds the minimal detectable
change (ADR-0003). ``data/subject/mdc.yaml`` (written by ``openacl compare``) takes precedence
over the literature defaults in :data:`openacl.core.mdc.DEFAULT_MDC`.
"""

from __future__ import annotations

import datetime as _dt
import math
import warnings as _warnings
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np
import yaml
from scipy import stats

from openacl.core.deviation import (
    gait_profile_score_deg,
    gait_variable_score_deg,
    pct_outside_2sd,
)
from openacl.core.events import SIDES
from openacl.core.mdc import DEFAULT_MDC
from openacl.core.normband import NormBand
from openacl.core.pipeline import LOADING_RESPONSE_END_PCT, GaitAnalysis
from openacl.core.symmetry import gait_asymmetry_pct, symmetry_index_pct
from openacl.schema import Side
from openacl.session.model import Session
from openacl.session.process import PassResult

PoolingMode = Literal["camera_near", "all_sides"]

DEFAULT_STANCE_PCT = 60.0
"""Fallback stance share when a cycle has no measured toe-off (Perry & Burnfield)."""

CURVE_CHANNELS: tuple[str, ...] = (
    "knee_flexion_deg",
    "hip_flexion_deg",
    "ankle_dorsiflexion_deg",
)
"""Channels shown as mean curves in the report; others are still scored if a band exists."""

CHANNEL_LABELS_DE: dict[str, str] = {
    "knee_flexion_deg": "Knieflexion",
    "hip_flexion_deg": "Hüftflexion",
    "ankle_dorsiflexion_deg": "Sprunggelenk Dorsalextension",
    "trunk_lean_deg": "Rumpfneigung",
}

MDC_SOURCE_OWN = "eigene Wiederholungsmessung"


@dataclass(frozen=True)
class MetricSpec:
    """One session key figure: its unit, its German label and the MDC entry it is judged by."""

    name: str
    unit: str
    label_de: str
    mdc_key: str | None
    """Key into ``data/subject/mdc.yaml`` / :data:`openacl.core.mdc.DEFAULT_MDC`."""
    kind: Literal["temporal", "spatial", "angle"]
    channel: str | None = None
    """Angle channel a curve metric is derived from."""


METRICS: tuple[MetricSpec, ...] = (
    MetricSpec("stance_pct", "%", "Standphase", "stance_pct", "temporal"),
    MetricSpec("swing_pct", "%", "Schwungphase", "swing_pct", "temporal"),
    MetricSpec("double_support_pct", "%", "Doppelstütz", "double_support_pct", "temporal"),
    MetricSpec("stride_time_s", "s", "Stride-Zeit", "stride_time_s", "temporal"),
    MetricSpec("swing_time_s", "s", "Schwungzeit", None, "temporal"),
    MetricSpec("cadence_steps_per_min", "Schritte/min", "Kadenz", None, "temporal"),
    MetricSpec("step_length_m", "m", "Schrittlänge", None, "spatial"),
    MetricSpec("stride_length_m", "m", "Stride-Länge", None, "spatial"),
    MetricSpec("walking_speed_m_s", "m/s", "Geschwindigkeit", "walking_speed_m_s", "spatial"),
    MetricSpec(
        "knee_flexion_at_initial_contact_deg",
        "°",
        "Knieflexion bei Initialkontakt",
        "sagittal_joint_angle_deg",
        "angle",
        "knee_flexion_deg",
    ),
    MetricSpec(
        "peak_knee_flexion_loading_deg",
        "°",
        "Peak Knieflexion Loading Response (0-30 %)",
        "peak_knee_flexion_deg",
        "angle",
        "knee_flexion_deg",
    ),
    MetricSpec(
        "min_knee_flexion_midstance_deg",
        "°",
        "Minimum Knieflexion mittlere Standphase",
        "sagittal_joint_angle_deg",
        "angle",
        "knee_flexion_deg",
    ),
    MetricSpec(
        "peak_knee_flexion_swing_deg",
        "°",
        "Peak Knieflexion Schwung",
        "peak_knee_flexion_deg",
        "angle",
        "knee_flexion_deg",
    ),
    MetricSpec(
        "knee_rom_deg", "°", "Knie-ROM", "sagittal_joint_angle_deg", "angle", "knee_flexion_deg"
    ),
    MetricSpec(
        "peak_hip_flexion_deg",
        "°",
        "Peak Hüftflexion",
        "sagittal_joint_angle_deg",
        "angle",
        "hip_flexion_deg",
    ),
    MetricSpec(
        "peak_hip_extension_deg",
        "°",
        "Peak Hüftextension (Minimum)",
        "sagittal_joint_angle_deg",
        "angle",
        "hip_flexion_deg",
    ),
    MetricSpec(
        "peak_ankle_dorsiflexion_deg",
        "°",
        "Peak Dorsalextension",
        "sagittal_joint_angle_deg",
        "angle",
        "ankle_dorsiflexion_deg",
    ),
    MetricSpec(
        "peak_ankle_plantarflexion_deg",
        "°",
        "Peak Plantarflexion (Minimum)",
        "sagittal_joint_angle_deg",
        "angle",
        "ankle_dorsiflexion_deg",
    ),
)

METRICS_BY_NAME: dict[str, MetricSpec] = {m.name: m for m in METRICS}
TEMPORAL_METRIC_NAMES: tuple[str, ...] = tuple(
    m.name for m in METRICS if m.kind in ("temporal", "spatial")
)
ANGLE_METRIC_NAMES: tuple[str, ...] = tuple(m.name for m in METRICS if m.kind == "angle")


# --------------------------------------------------------------------------- small helpers
def symmetry_index_operated_pct(x_operated: float, x_contralateral: float) -> float:
    """Robinson 1987 Symmetry Index, signed so that **positive = operated side larger**.

    ``SI_op = (X_op - X_contra) / (0.5 * (|X_op| + |X_contra|)) * 100``. This is
    :func:`openacl.core.symmetry.symmetry_index_pct` with the operated limb in the "right"
    slot, so the two functions cannot drift apart.
    """
    return symmetry_index_pct(x_left=x_contralateral, x_right=x_operated)


def other_side(side: Side) -> Side:
    return "R" if side == "L" else "L"


@dataclass(frozen=True)
class Estimate:
    """Mean, SD, n and the 95 % confidence interval of the mean of one pooled key figure."""

    mean: float
    sd: float
    n: int
    ci95_low: float
    ci95_high: float
    unit: str = ""

    @classmethod
    def from_values(cls, values: Iterable[float], unit: str = "") -> Estimate:
        v = np.asarray(list(values), dtype=float)
        v = v[np.isfinite(v)]
        if v.size == 0:
            nan = float("nan")
            return cls(nan, nan, 0, nan, nan, unit)
        mean = float(np.mean(v))
        if v.size < 2:
            return cls(mean, float("nan"), 1, float("nan"), float("nan"), unit)
        sd = float(np.std(v, ddof=1))
        half = float(stats.t.ppf(0.975, v.size - 1)) * sd / math.sqrt(v.size)
        return cls(mean, sd, int(v.size), mean - half, mean + half, unit)

    @property
    def valid(self) -> bool:
        return self.n > 0 and np.isfinite(self.mean)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mean": self.mean,
            "sd": self.sd,
            "n_cycles": self.n,
            "ci95_low": self.ci95_low,
            "ci95_high": self.ci95_high,
            "unit": self.unit,
        }


@dataclass(frozen=True)
class MdcEntry:
    """The minimal detectable change used to judge one metric, with where it comes from."""

    value: float
    unit: str
    source: str
    origin: Literal["own", "literature"]
    placeholder: bool = False
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit,
            "source": self.source,
            "origin": self.origin,
            "placeholder": self.placeholder,
            "note": self.note,
        }


@dataclass(frozen=True)
class SymmetryEntry:
    """Operated vs. contralateral difference of one metric, with its MDC verdict."""

    metric: str
    operated: Estimate
    contralateral: Estimate
    delta: float
    """``operated - contralateral`` in the metric's unit."""
    si_operated_pct: float
    mdc: MdcEntry | None
    above_mdc: bool
    operated_side_known: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "operated": self.operated.to_dict(),
            "contralateral": self.contralateral.to_dict(),
            "delta_operated_minus_contralateral": self.delta,
            "symmetry_index_operated_pct": self.si_operated_pct,
            "mdc": self.mdc.to_dict() if self.mdc else None,
            "above_mdc": self.above_mdc,
            "operated_side_known": self.operated_side_known,
        }


@dataclass(eq=False)
class PooledCycles:
    """Per-side pool of valid cycles: their curves, their per-cycle key figures, their origin."""

    phase_pct: np.ndarray
    curves: dict[Side, dict[str, np.ndarray]] = field(default_factory=dict)
    """``curves["R"]["knee_flexion_deg"]`` has shape ``(n_cycles, 101)``."""
    values: dict[Side, dict[str, np.ndarray]] = field(default_factory=dict)
    """``values["R"]["stance_pct"]`` has shape ``(n_cycles,)``, one entry per pooled cycle."""
    pass_of_cycle: dict[Side, list[str]] = field(default_factory=dict)
    n_dropped: dict[Side, int] = field(default_factory=dict)
    nan_pct: dict[Side, float] = field(default_factory=dict)

    def n_cycles(self, side: Side) -> int:
        return len(self.pass_of_cycle.get(side, []))

    def mean_curve_deg(self, channel: str, side: Side) -> np.ndarray | None:
        arr = self.curves.get(side, {}).get(channel)
        if arr is None or arr.size == 0:
            return None
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore", RuntimeWarning)
            return np.nanmean(arr, axis=0)

    def sd_curve_deg(self, channel: str, side: Side) -> np.ndarray | None:
        arr = self.curves.get(side, {}).get(channel)
        if arr is None or arr.shape[0] < 2:
            return None
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore", RuntimeWarning)
            return np.nanstd(arr, axis=0, ddof=1)

    def channels(self, side: Side) -> tuple[str, ...]:
        return tuple(sorted(self.curves.get(side, {})))


# ------------------------------------------------------------------ per-cycle key figures
def _window_extreme(
    curve: np.ndarray, phase_pct: np.ndarray, lo: float, hi: float, mode: str
) -> float:
    mask = np.isfinite(curve) & (phase_pct >= lo) & (phase_pct <= hi)
    if not mask.any():
        return float("nan")
    return float(np.max(curve[mask]) if mode == "max" else np.min(curve[mask]))


def cycle_angle_metrics(
    curve: np.ndarray, phase_pct: np.ndarray, channel: str, stance_pct: float
) -> dict[str, float]:
    """Discrete values of one time-normalised cycle curve.

    Windows follow Perry & Burnfield: loading response 0-30 % of the cycle, mid/terminal stance
    from 30 % to toe-off (the measured ``stance_pct`` of that cycle), swing after toe-off.
    """
    out: dict[str, float] = {}
    if not np.isfinite(stance_pct) or not (20.0 < stance_pct < 90.0):
        stance_pct = DEFAULT_STANCE_PCT
    finite = np.isfinite(curve)
    if channel == "knee_flexion_deg":
        first = np.flatnonzero(finite)
        out["knee_flexion_at_initial_contact_deg"] = (
            float(curve[first[0]]) if first.size else float("nan")
        )
        out["peak_knee_flexion_loading_deg"] = _window_extreme(
            curve, phase_pct, 0.0, LOADING_RESPONSE_END_PCT, "max"
        )
        out["min_knee_flexion_midstance_deg"] = _window_extreme(
            curve, phase_pct, LOADING_RESPONSE_END_PCT, stance_pct, "min"
        )
        out["peak_knee_flexion_swing_deg"] = _window_extreme(
            curve, phase_pct, stance_pct, 100.0, "max"
        )
        out["knee_rom_deg"] = (
            float(np.nanmax(curve) - np.nanmin(curve)) if finite.any() else float("nan")
        )
    elif channel == "hip_flexion_deg":
        out["peak_hip_flexion_deg"] = float(np.nanmax(curve)) if finite.any() else float("nan")
        out["peak_hip_extension_deg"] = float(np.nanmin(curve)) if finite.any() else float("nan")
    elif channel == "ankle_dorsiflexion_deg":
        out["peak_ankle_dorsiflexion_deg"] = (
            float(np.nanmax(curve)) if finite.any() else float("nan")
        )
        out["peak_ankle_plantarflexion_deg"] = (
            float(np.nanmin(curve)) if finite.any() else float("nan")
        )
    return out


def _pass_side_pool(
    analysis: GaitAnalysis, side: Side
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], int, float]:
    """Valid-cycle curves and per-cycle key figures of one side of one pass."""
    cycles = analysis.cycles
    mask = cycles.valid_mask(side)
    n_valid = int(mask.sum())
    n_dropped = int(mask.size - n_valid)
    if n_valid == 0:
        return {}, {}, n_dropped, float("nan")

    curves: dict[str, np.ndarray] = {}
    for channel, arr in cycles.curves.get(side, {}).items():
        if arr.size and arr.shape[0] == mask.size:
            curves[channel] = arr[mask]

    values: dict[str, np.ndarray] = {}
    per_stride = analysis.spatiotemporal.per_stride.get(side, {})
    for name in TEMPORAL_METRIC_NAMES:
        series = per_stride.get(name)
        if series is None or series.size != mask.size:
            values[name] = np.full(n_valid, np.nan)
        else:
            values[name] = np.asarray(series, dtype=float)[mask]

    stance = values.get("stance_pct", np.full(n_valid, np.nan))
    for name in ANGLE_METRIC_NAMES:
        values[name] = np.full(n_valid, np.nan)
    for channel, arr in curves.items():
        for k in range(arr.shape[0]):
            for name, value in cycle_angle_metrics(
                arr[k], cycles.phase_pct, channel, float(stance[k])
            ).items():
                if name in values:
                    values[name][k] = value

    nan_pct = float(
        np.mean([m.nan_pct for m in cycles.meta.get(side, []) if m.valid])
        if n_valid
        else float("nan")
    )
    return curves, values, n_dropped, nan_pct


def pool_cycles(
    results: Sequence[PassResult], pooling: PoolingMode = "camera_near"
) -> tuple[PooledCycles, list[str]]:
    """Pool the valid cycles of every successful pass, per side.

    ``pooling="camera_near"`` keeps only the side each pass reports as facing the camera; a
    pass whose backend could not determine that side contributes both legs and is warned about.
    """
    warnings: list[str] = []
    phase_pct = np.linspace(0.0, 100.0, 101)
    curve_parts: dict[Side, dict[str, list[np.ndarray]]] = {s: {} for s in SIDES}
    value_parts: dict[Side, dict[str, list[np.ndarray]]] = {s: {} for s in SIDES}
    pass_of_cycle: dict[Side, list[str]] = {s: [] for s in SIDES}
    dropped: dict[Side, int] = dict.fromkeys(SIDES, 0)
    nan_parts: dict[Side, list[float]] = {s: [] for s in SIDES}

    for outcome in results:
        analysis = outcome.analysis
        if analysis is None:
            continue
        phase_pct = analysis.cycles.phase_pct
        near = outcome.camera_near_side
        if pooling == "camera_near" and near is None:
            warnings.append(
                f"pass {outcome.name}: the backend did not report a camera-near side, "
                "both legs of this pass are pooled"
            )
        sides: tuple[Side, ...] = (
            SIDES if pooling == "all_sides" or near is None else (near,)  # type: ignore[assignment]
        )
        for side in sides:
            curves, values, n_dropped, nan_pct = _pass_side_pool(analysis, side)
            dropped[side] += n_dropped
            if not values:
                continue
            n_valid = len(next(iter(values.values())))
            pass_of_cycle[side].extend([outcome.name] * n_valid)
            if np.isfinite(nan_pct):
                nan_parts[side].append(nan_pct)
            for channel, arr in curves.items():
                curve_parts[side].setdefault(channel, []).append(arr)
            for name, arr in values.items():
                value_parts[side].setdefault(name, []).append(arr)

    pooled = PooledCycles(phase_pct=phase_pct, n_dropped=dropped)
    for side in SIDES:
        n_total = len(pass_of_cycle[side])
        pooled.pass_of_cycle[side] = pass_of_cycle[side]
        pooled.curves[side] = {
            channel: np.vstack(parts)
            for channel, parts in curve_parts[side].items()
            if sum(p.shape[0] for p in parts) == n_total
        }
        skipped = set(curve_parts[side]) - set(pooled.curves[side])
        if skipped:
            warnings.append(
                f"channel(s) {', '.join(sorted(skipped))} were missing in some passes on side "
                f"{side} and are excluded from the pooled curves"
            )
        pooled.values[side] = {
            name: np.concatenate(parts) if parts else np.array([])
            for name, parts in value_parts[side].items()
        }
        pooled.nan_pct[side] = float(np.mean(nan_parts[side])) if nan_parts[side] else float("nan")
    return pooled, warnings


# ------------------------------------------------------------------------------ MDC lookup
def load_subject_mdc(path: Path | str) -> dict[str, MdcEntry]:
    """Read ``data/subject/mdc.yaml`` written by ``openacl compare``; missing file -> ``{}``."""
    path = Path(path)
    if not path.exists():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}
    parameters = raw.get("parameters") if isinstance(raw, dict) else None
    if not isinstance(parameters, dict):
        return {}
    out: dict[str, MdcEntry] = {}
    for name, entry in parameters.items():
        if not isinstance(entry, dict):
            continue
        try:
            value = float(entry["value"])
        except (KeyError, TypeError, ValueError):
            continue
        if not np.isfinite(value):
            continue
        out[str(name)] = MdcEntry(
            value=value,
            unit=str(entry.get("unit", "")),
            source=str(entry.get("source", MDC_SOURCE_OWN)),
            origin="own",
            note=str(entry.get("note", "")),
        )
    return out


def resolve_mdc(spec: MetricSpec, subject_mdc: Mapping[str, MdcEntry]) -> MdcEntry | None:
    """Own repeat-measurement MDC first, literature default second, ``None`` if neither exists."""
    own = subject_mdc.get(spec.name) or (subject_mdc.get(spec.mdc_key) if spec.mdc_key else None)
    if own is not None:
        return own
    if spec.mdc_key is None:
        return None
    literature = DEFAULT_MDC.get(spec.mdc_key)
    if literature is None:
        return None
    return MdcEntry(
        value=literature.value,
        # DEFAULT_MDC spells its units "deg"/"pct"; the report shows the metric's own symbol
        unit=spec.unit,
        source=literature.source,
        origin="literature",
        placeholder=literature.placeholder,
        note=literature.note,
    )


def subject_mdc_path(session: Session) -> Path | None:
    """``<data>/subject/mdc.yaml`` for a session laid out as ``data/sessions/<name>``."""
    data_dir = session.data_dir
    return None if data_dir is None else data_dir / "subject" / "mdc.yaml"


# ------------------------------------------------------------------------- speed class
def resolve_speed_class(
    speed_m_s: float, height_m: float | None, normbands: Mapping[str, NormBand] | None
) -> tuple[str, str]:
    """Return ``(speed_class, how_it_was_determined)`` from the Froude number.

    Falls back to ``"comfortable"`` whenever speed, height or the tercile edges are missing.
    """
    from openacl.norm.bands import assign_speed_class, froude, leg_length_m

    if not np.isfinite(speed_m_s) or speed_m_s <= 0 or not height_m:
        return "comfortable", (
            "keine metrische Geschwindigkeit verfügbar, Normband-Klasse 'comfortable' als "
            "Annahme (subject.height_m im meta.yaml setzt die Skalierung)"
        )
    edges = None
    for band in (normbands or {}).values():
        candidate = band.meta.get("froude_edges")
        if candidate:
            edges = (float(candidate[0]), float(candidate[1]))
            break
    if edges is None:
        return "comfortable", (
            "Normbänder enthalten keine Froude-Grenzen, Klasse 'comfortable' als Annahme"
        )
    leg_m = float(leg_length_m(float("nan"), height_m))
    fr = float(froude(speed_m_s, leg_m))
    if not np.isfinite(fr):
        return "comfortable", "Froude-Zahl nicht berechenbar, Klasse 'comfortable' als Annahme"
    labels, used = assign_speed_class(np.array([fr]), edges=edges)
    label = labels[0] or "comfortable"

    def de(value: float, digits: int = 3) -> str:
        return f"{value:.{digits}f}".replace(".", ",")

    return str(label), (
        f"aus Froude-Zahl Fr = {de(fr)} (v = {de(speed_m_s, 2)} m/s, Beinlänge "
        f"{de(leg_m, 2)} m = 0,53 × Körperhöhe), Terzil-Grenzen {de(used[0])} / {de(used[1])}"
    )


def lookup_band(
    normbands: Mapping[str, NormBand], channel: str, side: Side, speed_class: str | None
) -> tuple[str, NormBand] | None:
    """Most specific norm band for ``channel``; mirrors ``openacl.core.deviation`` lookup order."""
    keys = [f"{channel}_{side}", channel]
    if speed_class:
        keys = [f"{channel}_{side}@{speed_class}", f"{channel}@{speed_class}", *keys]
    for key in keys:
        band = normbands.get(key)
        if band is not None:
            return key, band
    return None


# --------------------------------------------------------------------------- the summary
@dataclass(eq=False)
class SessionSummary:
    """All session key figures, serialisable to ``derived/session.json`` without NaN."""

    session_dir: str
    generated_utc: str
    meta: dict[str, Any]
    pooling: str
    operated_side: Side | None
    speed_class: str
    speed_class_source: str
    metrics: dict[str, dict[str, Estimate]] = field(default_factory=dict)
    """``metrics["stance_pct"]["L"]`` -> :class:`Estimate`."""
    symmetry: dict[str, SymmetryEntry] = field(default_factory=dict)
    gait_asymmetry_pct: float = float("nan")
    gvs_deg: dict[Side, dict[str, float]] = field(default_factory=dict)
    gps_deg: dict[Side, float] = field(default_factory=dict)
    pct_outside_2sd: dict[Side, dict[str, float]] = field(default_factory=dict)
    band_sources: dict[str, str] = field(default_factory=dict)
    curves: dict[str, dict[str, Any]] = field(default_factory=dict)
    """``curves["knee_flexion_deg"]["L"] = {"mean_deg": [...], "sd_deg": [...], ...}``."""
    norm_curves: dict[str, dict[str, Any]] = field(default_factory=dict)
    per_pass: list[dict[str, Any]] = field(default_factory=list)
    """One entry per pass with its own key figures -- the targets of the MDC design."""
    quality: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------- convenience
    @property
    def contralateral_side(self) -> Side | None:
        return other_side(self.operated_side) if self.operated_side else None

    def estimate(self, metric: str, side: Side) -> Estimate | None:
        return self.metrics.get(metric, {}).get(side)

    def n_cycles(self, side: Side) -> int:
        return int(self.quality.get("n_cycles", {}).get(side, 0))

    def to_dict(self) -> dict[str, Any]:
        return json_safe(
            {
                "schema": "openacl.session.v1",
                "session_dir": self.session_dir,
                "generated_utc": self.generated_utc,
                "meta": self.meta,
                "pooling": self.pooling,
                "operated_side": self.operated_side,
                "speed_class": self.speed_class,
                "speed_class_source": self.speed_class_source,
                "metrics": {
                    name: {side: est.to_dict() for side, est in per_side.items()}
                    for name, per_side in self.metrics.items()
                },
                "symmetry": {name: entry.to_dict() for name, entry in self.symmetry.items()},
                "gait_asymmetry_pct": self.gait_asymmetry_pct,
                "deviation": {
                    "gvs_deg": self.gvs_deg,
                    "gps_deg": self.gps_deg,
                    "pct_outside_2sd": self.pct_outside_2sd,
                    "band_sources": self.band_sources,
                    "source": "Baker et al. 2009, Gait Posture 30(3):265-269",
                },
                "curves": self.curves,
                "norm_curves": self.norm_curves,
                "per_pass": self.per_pass,
                "quality": self.quality,
                "warnings": self.warnings,
            }
        )

    def write_json(self, path: Path | str) -> Path:
        import json

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        return path


def json_safe(obj: Any) -> Any:
    """Recursively convert to plain JSON types; every non-finite float becomes ``None``."""
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [json_safe(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return [json_safe(v) for v in obj.tolist()]
    if isinstance(obj, np.generic):
        return json_safe(obj.item())
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, int | str | bool) or obj is None:
        return obj
    if isinstance(obj, Path):
        return str(obj)
    return str(obj)


# ----------------------------------------------------------------------------- aggregation
def _pass_metrics(results: Sequence[PassResult], pooling: PoolingMode) -> list[dict[str, Any]]:
    """Per-pass key figures -- the repeated-measurement targets ``openacl compare`` needs."""
    per_pass: list[dict[str, Any]] = []
    for outcome in results:
        entry: dict[str, Any] = {
            "name": outcome.name,
            "error": outcome.error,
            "cached": outcome.cached,
            "transcoded": outcome.transcoded,
            "runtime_s": outcome.runtime_s,
            "camera_near_side": outcome.camera_near_side,
            "walking_direction": (
                outcome.kinematics.walking_direction if outcome.kinematics else None
            ),
            "fps": outcome.kinematics.fps if outcome.kinematics else None,
            "warnings": list(outcome.warnings),
            "n_cycles": {},
            "n_dropped_cycles": {},
            "metrics": {},
        }
        if outcome.analysis is not None:
            pooled, _ = pool_cycles([outcome], pooling)
            entry["warnings"].extend(outcome.analysis.warnings)
            for side in SIDES:
                n = pooled.n_cycles(side)
                entry["n_cycles"][side] = n
                entry["n_dropped_cycles"][side] = pooled.n_dropped.get(side, 0)
                if n == 0:
                    continue
                entry["metrics"][side] = {
                    spec.name: Estimate.from_values(
                        pooled.values[side].get(spec.name, np.array([])), spec.unit
                    ).mean
                    for spec in METRICS
                }
        per_pass.append(entry)
    return per_pass


def aggregate_session(
    session: Session,
    results: Sequence[PassResult],
    *,
    normbands: Mapping[str, NormBand] | None = None,
    pooling: PoolingMode = "camera_near",
    speed_class: str | None = None,
    subject_mdc: Mapping[str, MdcEntry] | None = None,
) -> SessionSummary:
    """Pool every valid cycle of ``results`` and derive the session key figures.

    ``speed_class`` overrides the automatic Froude classification; ``subject_mdc`` overrides
    the file lookup (used by the tests).
    """
    pooled, warnings = pool_cycles(results, pooling)
    warnings = list(session.meta.warnings) + list(session.warnings) + warnings

    operated: Side | None = session.meta.operated_side
    op_side: Side = operated or "R"
    contra_side: Side = other_side(op_side)

    metrics: dict[str, dict[str, Estimate]] = {}
    for spec in METRICS:
        per_side: dict[str, Estimate] = {}
        for side in SIDES:
            values = pooled.values.get(side, {}).get(spec.name)
            if values is None or values.size == 0:
                continue
            estimate = Estimate.from_values(values, spec.unit)
            if estimate.n:
                per_side[side] = estimate
        if per_side:
            metrics[spec.name] = per_side

    speed = metrics.get("walking_speed_m_s", {})
    speed_values = [e.mean for e in speed.values() if e.valid]
    mean_speed = float(np.mean(speed_values)) if speed_values else float("nan")
    if speed_class is None:
        resolved_class, class_source = resolve_speed_class(
            mean_speed, session.meta.subject.height_m, normbands
        )
    else:
        resolved_class, class_source = speed_class, "manuell über --speed-class gesetzt"
    if "Annahme" in class_source:
        warnings.append(class_source)

    if subject_mdc is None:
        mdc_path = subject_mdc_path(session)
        subject_mdc = load_subject_mdc(mdc_path) if mdc_path else {}
    if subject_mdc:
        warnings.append(
            f"{len(subject_mdc)} MDC-Wert(e) aus eigener Wiederholungsmessung werden "
            "gegenüber den Literaturwerten bevorzugt"
        )

    symmetry: dict[str, SymmetryEntry] = {}
    for spec in METRICS:
        per_side = metrics.get(spec.name, {})
        op, contra = per_side.get(op_side), per_side.get(contra_side)
        if op is None or contra is None or not (op.valid and contra.valid):
            continue
        delta = op.mean - contra.mean
        mdc = resolve_mdc(spec, subject_mdc)
        symmetry[spec.name] = SymmetryEntry(
            metric=spec.name,
            operated=op,
            contralateral=contra,
            delta=delta,
            si_operated_pct=symmetry_index_operated_pct(op.mean, contra.mean),
            mdc=mdc,
            above_mdc=bool(mdc is not None and abs(delta) > abs(mdc.value)),
            operated_side_known=operated is not None,
        )

    swing = metrics.get("swing_time_s", {})
    ga = gait_asymmetry_pct(
        swing["L"].mean if "L" in swing else float("nan"),
        swing["R"].mean if "R" in swing else float("nan"),
    )

    gvs: dict[Side, dict[str, float]] = {s: {} for s in SIDES}
    outside: dict[Side, dict[str, float]] = {s: {} for s in SIDES}
    gps: dict[Side, float] = {s: float("nan") for s in SIDES}
    band_sources: dict[str, str] = {}
    norm_curves: dict[str, dict[str, Any]] = {}
    missing: set[str] = set()
    for side in SIDES:
        for channel in pooled.channels(side):
            curve = pooled.mean_curve_deg(channel, side)
            if curve is None:
                continue
            hit = lookup_band(normbands or {}, channel, side, resolved_class)
            if hit is None:
                missing.add(channel)
                continue
            key, band = hit
            if curve.shape != band.mean.shape:
                warnings.append(
                    f"Normband {key!r} hat {band.n_points} Punkte, die Kurve {curve.size}; "
                    "Kanal übersprungen"
                )
                continue
            gvs[side][channel] = gait_variable_score_deg(curve, band)
            outside[side][channel] = pct_outside_2sd(curve, band)
            band_sources[key] = band.source
            norm_curves.setdefault(
                channel,
                {
                    "mean_deg": band.mean.tolist(),
                    "sd_deg": band.sd.tolist(),
                    "n_subjects": band.n,
                    "source": band.source,
                    "speed_class": resolved_class,
                },
            )
        gps[side] = gait_profile_score_deg(gvs[side])
    if missing:
        warnings.append("kein Normband für Kanal/Kanäle: " + ", ".join(sorted(missing)))
    if not normbands:
        warnings.append("keine Normbänder geladen, GVS und GPS entfallen")

    curves: dict[str, dict[str, Any]] = {}
    for channel in CURVE_CHANNELS:
        for side in SIDES:
            mean_curve = pooled.mean_curve_deg(channel, side)
            if mean_curve is None:
                continue
            sd_curve = pooled.sd_curve_deg(channel, side)
            curves.setdefault(channel, {})[side] = {
                "mean_deg": mean_curve.tolist(),
                "sd_deg": (sd_curve.tolist() if sd_curve is not None else None),
                "n_cycles": pooled.n_cycles(side),
            }

    ok = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]
    fps_values = sorted({round(float(r.kinematics.fps), 3) for r in ok if r.kinematics})
    quality = {
        "n_passes_total": len(results),
        "n_passes_ok": len(ok),
        "n_passes_failed": len(failed),
        "failed_passes": {r.name: r.error for r in failed},
        "n_cycles": {s: pooled.n_cycles(s) for s in SIDES},
        "n_dropped_cycles": {s: pooled.n_dropped.get(s, 0) for s in SIDES},
        "mean_nan_pct": {s: pooled.nan_pct.get(s, float("nan")) for s in SIDES},
        "fps": fps_values,
        "fps_meta_camera_a": session.meta.camera_fps("A"),
        "camera_b_passes": [p.name for p in session.passes_b],
        "cycles_per_pass": {
            s: {
                name: pooled.pass_of_cycle[s].count(name)
                for name in sorted(set(pooled.pass_of_cycle[s]))
            }
            for s in SIDES
        },
        "phase_points": int(pooled.phase_pct.size),
    }

    return SessionSummary(
        session_dir=str(session.root),
        generated_utc=_dt.datetime.now(_dt.UTC).isoformat(timespec="seconds"),
        meta=session.meta.as_dict(),
        pooling=pooling,
        operated_side=operated,
        speed_class=resolved_class,
        speed_class_source=class_source,
        metrics=metrics,
        symmetry=symmetry,
        gait_asymmetry_pct=ga,
        gvs_deg=gvs,
        gps_deg=gps,
        pct_outside_2sd=outside,
        band_sources=band_sources,
        curves=curves,
        norm_curves=norm_curves,
        per_pass=_pass_metrics(results, pooling),
        quality=quality,
        warnings=warnings,
    )

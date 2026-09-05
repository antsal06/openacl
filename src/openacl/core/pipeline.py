"""Gait-core entry point: ``KinematicsResult`` in, ``GaitAnalysis`` out.

Order of operations (see docs/00-SYNTHESE.md section 3):
filter -> events -> cycles -> spatio-temporal -> symmetry -> deviation.

This module imports nothing from ``openacl.backends``; layer 3 stays backend-independent
(ADR-0007).
"""

from __future__ import annotations

import warnings as _warnings
from collections.abc import Mapping
from dataclasses import dataclass, field, replace

import numpy as np

from openacl.schema import KinematicsResult, Side, sided

from .cycles import GaitCycles, normalize_cycles
from .deviation import DeviationResult, compute_deviation
from .events import SIDES, GaitEvents, detect_events
from .filtering import DEFAULT_CUTOFF_HZ, DEFAULT_MAX_GAP_S, lowpass, lowpass_columns
from .normband import NormBand
from .spatiotemporal import Spatiotemporal, compute_spatiotemporal
from .symmetry import SymmetryResult, compute_symmetry

MIN_VALID_CYCLES = 10
"""Below this a session is flagged; docs/00-SYNTHESE.md section 2.1 asks for 20-40 cycles."""

LOW_CONFIDENCE = 0.6

LOADING_RESPONSE_END_PCT = 30.0
"""End of the loading-response window used for the peak knee flexion in stance (Perry)."""

DISCRETE_KNEE_PARAMS: tuple[str, ...] = (
    "knee_flexion_at_initial_contact_deg",
    "peak_knee_flexion_loading_deg",
    "peak_knee_flexion_swing_deg",
    "knee_rom_deg",
)


@dataclass(eq=False)
class GaitAnalysis:
    """Everything gait-core derives from one walking pass."""

    events: GaitEvents
    cycles: GaitCycles
    spatiotemporal: Spatiotemporal
    symmetry: SymmetryResult
    deviation: DeviationResult
    discrete_deg: dict[Side, dict[str, float]] = field(default_factory=dict)
    """Discrete curve values per side, e.g. peak knee flexion in swing."""
    operated_side: Side | None = None
    warnings: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    @property
    def n_valid_cycles(self) -> dict[Side, int]:
        return {s: self.cycles.n_valid(s) for s in SIDES}


def filter_result(
    result: KinematicsResult,
    cutoff_hz: float = DEFAULT_CUTOFF_HZ,
    order: int = 4,
    max_gap_s: float = DEFAULT_MAX_GAP_S,
) -> KinematicsResult:
    """Return a copy of ``result`` with all angle and keypoint traces low-pass filtered."""
    fps = float(result.fps)
    angles = {
        name: lowpass(series, fps, cutoff_hz=cutoff_hz, order=order, max_gap_s=max_gap_s)
        for name, series in result.angles_deg.items()
    }
    keypoints = {
        name: lowpass_columns(arr, fps, cutoff_hz=cutoff_hz, order=order, max_gap_s=max_gap_s)
        for name, arr in result.keypoints.items()
    }
    meta = dict(result.meta)
    meta["gait_core_filter"] = {
        "type": "butterworth zero-phase low pass",
        "order": order,
        "cutoff_hz": cutoff_hz,
        "max_interpolated_gap_s": max_gap_s,
    }
    return replace(result, angles_deg=angles, keypoints=keypoints, meta=meta)


def _discrete_curve_values(
    cycles: GaitCycles, spatiotemporal: Spatiotemporal
) -> dict[Side, dict[str, float]]:
    """Discrete knee values from the per-side mean curve, split at the measured stance end."""
    out: dict[Side, dict[str, float]] = {}
    for side in SIDES:
        curve = cycles.mean_curve_deg("knee_flexion_deg", side)
        if curve is None or not np.isfinite(curve).any():
            continue
        stance_pct = spatiotemporal.side(side).stance_pct.mean
        if not np.isfinite(stance_pct):
            stance_pct = 60.0
        phase = cycles.phase_pct
        loading = np.isfinite(curve) & (phase <= LOADING_RESPONSE_END_PCT)
        swing = np.isfinite(curve) & (phase > stance_pct)
        values: dict[str, float] = {}
        first = np.flatnonzero(np.isfinite(curve))
        values["knee_flexion_at_initial_contact_deg"] = float(curve[first[0]])
        values["peak_knee_flexion_loading_deg"] = (
            float(np.max(curve[loading])) if loading.any() else float("nan")
        )
        values["peak_knee_flexion_swing_deg"] = (
            float(np.max(curve[swing])) if swing.any() else float("nan")
        )
        values["knee_rom_deg"] = float(np.nanmax(curve) - np.nanmin(curve))
        out[side] = values
    return out


def _confidence_warnings(result: KinematicsResult) -> list[str]:
    warnings: list[str] = []
    if not result.confidence:
        return ["backend delivered no per-keypoint confidence, quality cannot be judged"]
    for side in SIDES:
        keys = [sided(n, side) for n in ("hip", "knee", "ankle", "heel", "big_toe")]
        values = [result.confidence[k] for k in keys if k in result.confidence]
        if not values:
            continue
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore", RuntimeWarning)
            mean_conf = float(np.nanmean(np.concatenate(values)))
        if not np.isfinite(mean_conf):
            continue
        far = result.camera_near_side is not None and result.camera_near_side != side
        if mean_conf < LOW_CONFIDENCE:
            where = "camera-far leg" if far else "leg"
            warnings.append(
                f"low keypoint confidence on the {where} {side} "
                f"(mean {mean_conf:.2f} < {LOW_CONFIDENCE:.2f}); "
                "values of this side are less reliable"
            )
        elif far:
            warnings.append(
                f"side {side} faces away from the camera; occlusion makes it less reliable "
                "than the camera-near side"
            )
    return warnings


def analyze(
    result: KinematicsResult,
    operated_side: Side | None = None,
    normbands: Mapping[str, NormBand] | None = None,
    *,
    speed_class: str | None = None,
    cutoff_hz: float = DEFAULT_CUTOFF_HZ,
    min_valid_cycles: int = MIN_VALID_CYCLES,
) -> GaitAnalysis:
    """Run the whole gait-core chain on one walking pass.

    Parameters
    ----------
    result
        Backend output, see :class:`openacl.schema.KinematicsResult`.
    operated_side
        ``"L"`` / ``"R"`` so symmetry can be reported as operated vs. contralateral,
        or ``None`` when unknown.
    normbands
        Mapping channel name -> :class:`openacl.core.normband.NormBand`. Keys may carry a side
        suffix (``"knee_flexion_deg_L"``) or not (``"knee_flexion_deg"``). ``None`` skips the
        deviation scores.
    speed_class
        Speed class of the band set, e.g. ``"comfortable"``. Matches the
        ``"<channel>@<speed_class>"`` keys of ``openacl.norm.load_normbands``.
    """
    result.validate()
    filtered = filter_result(result, cutoff_hz=cutoff_hz)

    events = detect_events(filtered, smooth=False)
    cycles = normalize_cycles(filtered, events)
    valid_masks = {s: cycles.valid_mask(s) for s in SIDES}
    spatiotemporal = compute_spatiotemporal(filtered, events, valid_masks=valid_masks)
    discrete = _discrete_curve_values(cycles, spatiotemporal)

    extra = {
        name: (
            discrete.get("L", {}).get(name, float("nan")),
            discrete.get("R", {}).get(name, float("nan")),
        )
        for name in DISCRETE_KNEE_PARAMS
        if discrete
    }
    symmetry = compute_symmetry(spatiotemporal, cycles, operated_side, extra_values=extra)
    deviation = compute_deviation(cycles, normbands, speed_class=speed_class)

    warnings: list[str] = []
    warnings.extend(events.warnings)
    warnings.extend(cycles.warnings)
    warnings.extend(spatiotemporal.warnings)
    warnings.extend(symmetry.warnings)
    warnings.extend(deviation.warnings)
    warnings.extend(_confidence_warnings(result))
    if events.direction_source != "walking_direction":
        warnings.append(
            "walking direction was estimated from the hip displacement, "
            "the backend did not report it"
        )
    for side in SIDES:
        n_valid = cycles.n_valid(side)
        if n_valid < min_valid_cycles:
            warnings.append(
                f"only {n_valid} valid gait cycles on side {side} "
                f"(target >= {min_valid_cycles}; 20-40 per session is recommended)"
            )
        n_dropped = len(cycles.meta.get(side, [])) - n_valid
        if n_dropped:
            warnings.append(f"{n_dropped} cycle(s) on side {side} excluded as outliers")

    return GaitAnalysis(
        events=events,
        cycles=cycles,
        spatiotemporal=spatiotemporal,
        symmetry=symmetry,
        deviation=deviation,
        discrete_deg=discrete,
        operated_side=operated_side,
        warnings=warnings,
        meta={
            "backend": result.backend,
            "fps": result.fps,
            "n_frames": result.n_frames,
            "keypoint_unit": result.keypoint_unit,
            "camera_near_side": result.camera_near_side,
            "filter": filtered.meta.get("gait_core_filter"),
        },
    )

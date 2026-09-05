"""Gait event detection from foot and pelvis keypoints (Zeni et al. 2008).

Method
------
Zeni JA, Richards JG, Higginson JS (2008), "Two simple methods for determining gait events
during treadmill and overground walking using kinematic data", *Gait & Posture* 27(4):710-714.

With the pelvis (sacrum, here the mid-hip) as moving reference and ``x`` as the direction of
progression:

- heel strike  = local **maximum** of ``heel_x - sacrum_x``
- toe off      = local **minimum** of ``toe_x  - sacrum_x``

The direction of progression is taken from ``KinematicsResult.walking_direction`` when known,
otherwise estimated from the sign of the mid-hip displacement over the recording.

Plausibility filter
-------------------
Successive heel strikes of *alternating* sides must be ``min_step_time_s`` .. ``max_step_time_s``
apart (default 0.3-2.0 s). Events violating the lower bound are dropped as spurious, a violation
of the upper bound or a missing side alternation is reported in ``GaitEvents.warnings``.

Known systematic bias (validated 2026-09-05, ``docs/validation/core_vs_fukuchi.md``)
--------------------------------------------------------------------------------------
Against force-plate events of the Fukuchi 2018 overground data set (12 subjects, 3 speeds,
heel and MT1 markers) this implementation detects heel strike 37 +- 17 ms **early** and
toe off 19 +- 29 ms **late**. Stance phase is therefore overestimated by about
``KNOWN_STANCE_BIAS_PCT`` percentage points. The bias is the same for both sides, so
left/right symmetry indices are unaffected; absolute stance/swing percentages and
double-support estimates are not. Consumers comparing stance against norm bands must
subtract the bias or widen thresholds accordingly. Cadence and stride time are unbiased.
"""

from __future__ import annotations

import warnings as _warnings
from dataclasses import dataclass, field
from itertools import pairwise

import numpy as np
from scipy.signal import find_peaks

from openacl.schema import KinematicsResult, Side, sided

from .filtering import DEFAULT_CUTOFF_HZ, lowpass

SIDES: tuple[Side, Side] = ("L", "R")

MIN_STEP_TIME_S = 0.3
MAX_STEP_TIME_S = 2.0

KNOWN_STANCE_BIAS_PCT = 5.5
"""Stance-phase overestimation (percentage points) vs force plates, Fukuchi 2018, n=26 trials."""
KNOWN_STANCE_BIAS_SD_PCT = 1.25


@dataclass(frozen=True, eq=False)
class GaitEvents:
    """Frame indices and times of heel strikes and toe offs, per side."""

    fps: float
    heel_strikes_L: np.ndarray
    """Frame indices, ``int`` dtype, strictly increasing."""
    heel_strikes_R: np.ndarray
    toe_offs_L: np.ndarray
    toe_offs_R: np.ndarray
    heel_strike_times_L_s: np.ndarray
    heel_strike_times_R_s: np.ndarray
    toe_off_times_L_s: np.ndarray
    toe_off_times_R_s: np.ndarray
    direction_sign: int
    """``+1`` if the subject walks towards ``+x``, ``-1`` towards ``-x``."""
    direction_source: str
    """``"walking_direction"`` or ``"estimated_from_hip_displacement"``."""
    warnings: tuple[str, ...] = ()
    meta: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ helpers
    def heel_strikes(self, side: Side) -> np.ndarray:
        return self.heel_strikes_L if side == "L" else self.heel_strikes_R

    def toe_offs(self, side: Side) -> np.ndarray:
        return self.toe_offs_L if side == "L" else self.toe_offs_R

    def heel_strike_times_s(self, side: Side) -> np.ndarray:
        return self.heel_strike_times_L_s if side == "L" else self.heel_strike_times_R_s

    def toe_off_times_s(self, side: Side) -> np.ndarray:
        return self.toe_off_times_L_s if side == "L" else self.toe_off_times_R_s

    def n_strides(self, side: Side) -> int:
        return max(0, int(self.heel_strikes(side).size) - 1)


def _fill_for_detection(x: np.ndarray) -> np.ndarray:
    """Fill every NaN by linear interpolation / edge hold, for peak search only."""
    x = np.asarray(x, dtype=float)
    finite = np.isfinite(x)
    if finite.all():
        return x.copy()
    if not finite.any():
        return np.zeros_like(x)
    idx = np.arange(x.size, dtype=float)
    return np.interp(idx, idx[finite], x[finite])


def _mid_hip_x(result: KinematicsResult) -> np.ndarray:
    """Progression reference: mid-hip (sacrum proxy) x-trace, NaN-tolerant."""
    for name in ("sacrum", "pelvis", "mid_hip"):
        if name in result.keypoints:
            return np.asarray(result.keypoints[name][:, 0], dtype=float)
    available = [sided("hip", s) for s in SIDES if sided("hip", s) in result.keypoints]
    if not available:
        raise ValueError(
            "event detection needs a pelvis reference: keypoints 'hip_L'/'hip_R' or 'sacrum'"
        )
    stack = np.stack([np.asarray(result.keypoints[k][:, 0], dtype=float) for k in available])
    with _warnings.catch_warnings():
        _warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmean(stack, axis=0)


def estimate_direction_sign(result: KinematicsResult) -> tuple[int, str]:
    """Return ``(+1|-1, source)`` for the direction of progression along ``x``."""
    if result.walking_direction == "+x":
        return 1, "walking_direction"
    if result.walking_direction == "-x":
        return -1, "walking_direction"
    ref = _mid_hip_x(result)
    finite = np.isfinite(ref)
    if finite.sum() < 2:
        raise ValueError("cannot estimate walking direction: hip trace has < 2 valid frames")
    t = np.asarray(result.time_s, dtype=float)[finite]
    slope = float(np.polyfit(t, ref[finite], 1)[0])
    return (1 if slope >= 0 else -1), "estimated_from_hip_displacement"


def _peaks(signal: np.ndarray, fps: float, min_stride_time_s: float) -> np.ndarray:
    """Local maxima of ``signal`` at least ``min_stride_time_s`` apart, with prominence guard."""
    distance = max(1, round(min_stride_time_s * fps))
    span = float(np.nanpercentile(signal, 97.5) - np.nanpercentile(signal, 2.5))
    prominence = 0.1 * span if span > 0 else None
    idx, _ = find_peaks(signal, distance=distance, prominence=prominence)
    return idx.astype(int)


def _one_event_per_interval(candidates: np.ndarray, bounds: np.ndarray) -> np.ndarray:
    """Keep the first candidate inside each ``[bounds[k], bounds[k+1])`` plus outer candidates."""
    if candidates.size == 0 or bounds.size < 2:
        return candidates
    keep: list[int] = [int(c) for c in candidates if c < bounds[0] or c >= bounds[-1]]
    for lo, hi in pairwise(bounds):
        inside = candidates[(candidates >= lo) & (candidates < hi)]
        if inside.size:
            keep.append(int(inside[0]))
    return np.array(sorted(keep), dtype=int)


def _apply_step_plausibility(
    hs: dict[Side, np.ndarray], fps: float, min_step_time_s: float, max_step_time_s: float
) -> tuple[dict[Side, np.ndarray], list[str]]:
    """Drop heel strikes closer than ``min_step_time_s`` and report alternation problems."""
    merged = sorted(
        [(int(f), s) for s in SIDES for f in hs[s]],
        key=lambda item: item[0],
    )
    kept: list[tuple[int, Side]] = []
    warnings: list[str] = []
    min_frames = min_step_time_s * fps
    for frame, side in merged:
        if kept and (frame - kept[-1][0]) < min_frames:
            warnings.append(
                f"dropped heel strike {side} at frame {frame}: "
                f"step time < {min_step_time_s:.2f} s (spurious peak)"
            )
            continue
        kept.append((frame, side))
    for (f0, s0), (f1, s1) in pairwise(kept):
        step_time_s = (f1 - f0) / fps
        if s0 == s1:
            warnings.append(
                f"two consecutive heel strikes on side {s0} (frames {f0} and {f1}): "
                "a contralateral event is probably missing"
            )
        if step_time_s > max_step_time_s:
            warnings.append(
                f"step time {step_time_s:.2f} s between frames {f0} and {f1} "
                f"exceeds {max_step_time_s:.2f} s"
            )
    out = {s: np.array([f for f, side in kept if side == s], dtype=int) for s in SIDES}
    return out, warnings


def detect_events(
    result: KinematicsResult,
    *,
    smooth: bool = True,
    cutoff_hz: float = DEFAULT_CUTOFF_HZ,
    min_step_time_s: float = MIN_STEP_TIME_S,
    max_step_time_s: float = MAX_STEP_TIME_S,
) -> GaitEvents:
    """Detect heel strikes and toe offs after Zeni et al. 2008.

    Parameters
    ----------
    result
        Kinematics of one walking pass. Needs ``heel_L/R``, ``big_toe_L/R`` and a pelvis
        reference (``hip_L``/``hip_R`` or ``sacrum``) in ``keypoints``.
    smooth
        Low-pass the keypoint traces before the peak search. Set to ``False`` when the caller
        already filtered (as :func:`openacl.core.pipeline.analyze` does).
    """
    fps = float(result.fps)
    time_s = np.asarray(result.time_s, dtype=float)
    direction_sign, direction_source = estimate_direction_sign(result)
    ref_x = _mid_hip_x(result)
    if smooth:
        ref_x = lowpass(ref_x, fps, cutoff_hz=cutoff_hz)

    min_stride_time_s = 2.0 * min_step_time_s
    warnings: list[str] = []
    hs: dict[Side, np.ndarray] = {}
    to: dict[Side, np.ndarray] = {}

    for side in SIDES:
        heel_key, toe_key = sided("heel", side), sided("big_toe", side)
        for key in (heel_key, toe_key):
            if key not in result.keypoints:
                raise ValueError(f"event detection needs keypoint {key!r}")
        heel_x = np.asarray(result.keypoints[heel_key][:, 0], dtype=float)
        toe_x = np.asarray(result.keypoints[toe_key][:, 0], dtype=float)
        if smooth:
            heel_x = lowpass(heel_x, fps, cutoff_hz=cutoff_hz)
            toe_x = lowpass(toe_x, fps, cutoff_hz=cutoff_hz)

        heel_rel = _fill_for_detection(direction_sign * (heel_x - ref_x))
        toe_rel = _fill_for_detection(direction_sign * (toe_x - ref_x))
        nan_pct = 100.0 * float(np.mean(~np.isfinite(heel_x)))
        if nan_pct > 20.0:
            warnings.append(f"heel_{side} trace is {nan_pct:.0f} % NaN, events are unreliable")

        hs[side] = _peaks(heel_rel, fps, min_stride_time_s)
        to[side] = _peaks(-toe_rel, fps, min_stride_time_s)

    hs, step_warnings = _apply_step_plausibility(hs, fps, min_step_time_s, max_step_time_s)
    warnings.extend(step_warnings)
    for side in SIDES:
        to[side] = _one_event_per_interval(to[side], hs[side])
        if hs[side].size < 2:
            warnings.append(f"less than two heel strikes detected on side {side}")

    def times(frames: np.ndarray) -> np.ndarray:
        return time_s[frames] if frames.size else np.zeros(0, dtype=float)

    return GaitEvents(
        fps=fps,
        heel_strikes_L=hs["L"],
        heel_strikes_R=hs["R"],
        toe_offs_L=to["L"],
        toe_offs_R=to["R"],
        heel_strike_times_L_s=times(hs["L"]),
        heel_strike_times_R_s=times(hs["R"]),
        toe_off_times_L_s=times(to["L"]),
        toe_off_times_R_s=times(to["R"]),
        direction_sign=direction_sign,
        direction_source=direction_source,
        warnings=tuple(warnings),
        meta={"method": "Zeni et al. 2008, Gait & Posture 27:710-714"},
    )

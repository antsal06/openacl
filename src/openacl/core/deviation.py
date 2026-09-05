"""Deviation of measured curves from a norm band: Gait Variable Score and Gait Profile Score.

Baker R, McGinley JL, Schwartz MH, Beynon S, Rozumalski A, Graham HK, Tirosh O (2009),
"The Gait Profile Score and Movement Analysis Profile", *Gait & Posture* 30(3):265-269::

    GVS_k = sqrt( mean_over_phase( (x_k(t) - x_ref_k(t))^2 ) )      [deg]
    GPS    = sqrt( mean_over_k( GVS_k^2 ) )                          [deg]

The GVS is the RMS distance of one time-normalised curve to the reference mean curve over
0-100 % of the gait cycle; the GPS is the RMS over the available GVS. Reference for healthy
adults: GPS ~5-6 deg (Baker 2009, see docs/research/02, section 5).

``pct_outside_2sd`` additionally reports how much of the curve lies outside the +-2 SD band,
which is the intuitive "outside the norm band" number for the report.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np

from openacl.schema import Side

from .cycles import GaitCycles
from .events import SIDES
from .normband import NormBand


def gait_variable_score_deg(curve: np.ndarray, band: NormBand) -> float:
    """RMS distance of one time-normalised curve to the norm band mean, in degrees."""
    curve = np.asarray(curve, dtype=float)
    if curve.shape != band.mean.shape:
        raise ValueError(f"curve shape {curve.shape} != norm band shape {band.mean.shape}")
    diff = curve - band.mean
    finite = np.isfinite(diff)
    if not finite.any():
        return float("nan")
    return float(np.sqrt(np.mean(diff[finite] ** 2)))


def pct_outside_2sd(curve: np.ndarray, band: NormBand) -> float:
    """Percentage of the curve lying outside the +-2 SD norm band."""
    curve = np.asarray(curve, dtype=float)
    if curve.shape != band.mean.shape:
        raise ValueError(f"curve shape {curve.shape} != norm band shape {band.mean.shape}")
    finite = np.isfinite(curve)
    if not finite.any():
        return float("nan")
    outside = (curve < band.lower_2sd) | (curve > band.upper_2sd)
    return 100.0 * float(np.mean(outside[finite]))


def gait_profile_score_deg(gvs_deg: Mapping[str, float]) -> float:
    """RMS over the available Gait Variable Scores (Baker et al. 2009)."""
    values = np.asarray([v for v in gvs_deg.values() if np.isfinite(v)], dtype=float)
    if values.size == 0:
        return float("nan")
    return float(np.sqrt(np.mean(values**2)))


@dataclass(eq=False)
class DeviationResult:
    """GVS per channel and side, GPS per side, and the share outside the +-2 SD band."""

    gvs_deg: dict[Side, dict[str, float]]
    gps_deg: dict[Side, float]
    pct_outside_2sd: dict[Side, dict[str, float]]
    band_sources: dict[str, str] = field(default_factory=dict)
    missing_bands: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    source: str = "Baker et al. 2009, Gait Posture 30(3):265-269"


def _lookup_band(
    normbands: Mapping[str, NormBand], channel: str, side: Side, speed_class: str | None = None
) -> tuple[str, NormBand] | None:
    """Find the most specific band for ``channel``.

    Lookup order: side- and speed-specific (``knee_flexion_deg_L@comfortable``), speed-specific
    (``knee_flexion_deg@comfortable``, the key style of ``openacl.norm.load_normbands``),
    side-specific (``knee_flexion_deg_L``), generic (``knee_flexion_deg``).
    """
    keys = [f"{channel}_{side}", channel]
    if speed_class:
        keys = [f"{channel}_{side}@{speed_class}", f"{channel}@{speed_class}", *keys]
    for key in keys:
        band = normbands.get(key)
        if band is not None:
            return key, band
    return None


def compute_deviation(
    cycles: GaitCycles,
    normbands: Mapping[str, NormBand] | None,
    *,
    speed_class: str | None = None,
    only_valid: bool = True,
) -> DeviationResult:
    """Compare the per-side mean curves against the given norm bands.

    ``speed_class`` selects a speed-normalised band set (ADR-0003); it matches the
    ``"<channel>@<speed_class>"`` keys produced by ``openacl.norm.load_normbands``.
    """
    gvs: dict[Side, dict[str, float]] = {s: {} for s in SIDES}
    outside: dict[Side, dict[str, float]] = {s: {} for s in SIDES}
    gps: dict[Side, float] = {s: float("nan") for s in SIDES}
    sources: dict[str, str] = {}
    missing: set[str] = set()
    warnings: list[str] = []

    if not normbands:
        return DeviationResult(
            gvs_deg=gvs,
            gps_deg=gps,
            pct_outside_2sd=outside,
            missing_bands=(),
            warnings=("no norm bands provided, deviation scores are not computed",),
        )

    for side in SIDES:
        for channel in cycles.channels(side):
            hit = _lookup_band(normbands, channel, side, speed_class)
            if hit is None:
                missing.add(channel)
                continue
            key, band = hit
            curve = cycles.mean_curve_deg(channel, side, only_valid=only_valid)
            if curve is None:
                continue
            if curve.shape != band.mean.shape:
                warnings.append(
                    f"norm band {key!r} has {band.n_points} points, curve has {curve.size}; "
                    "channel skipped"
                )
                continue
            gvs[side][channel] = gait_variable_score_deg(curve, band)
            outside[side][channel] = pct_outside_2sd(curve, band)
            sources[key] = band.source
        gps[side] = gait_profile_score_deg(gvs[side])

    if missing:
        warnings.append("no norm band for channel(s): " + ", ".join(sorted(missing)))
    return DeviationResult(
        gvs_deg=gvs,
        gps_deg=gps,
        pct_outside_2sd=outside,
        band_sources=sources,
        missing_bands=tuple(sorted(missing)),
        warnings=tuple(warnings),
    )

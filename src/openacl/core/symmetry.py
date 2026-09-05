"""Between-limb symmetry measures.

Symmetry Index (SI), Robinson RO, Herzog W, Nigg BM (1987), *J Manipulative Physiol Ther*
10:172-176::

    SI = (X_R - X_L) / (0.5 * (|X_R| + |X_L|)) * 100   [%]

Sign convention used here: **positive SI means the value is larger on the RIGHT**.
0 % is perfect symmetry, ±100 % is a very large asymmetry. The measure has no time-shift
correction, which is its known limitation.

Gait Asymmetry (GA), Yogev G, Plotnik M et al. (2007), *Exp Brain Res* 177:336-346::

    GA = 100 * |ln(SW_R / SW_L)|   [%]

on the swing times of both sides. GA is always >= 0 and carries no direction.

Curve symmetry: RMS difference between the left and right mean curve of one channel over
0-100 % of the gait cycle, in degrees. This is the same distance measure the Gait Variable
Score uses (Baker et al. 2009), but with the contralateral limb instead of a norm band as
reference. Careful: after ACL reconstruction the contralateral limb is not a clean reference,
it compensates (see docs/00-SYNTHESE.md section 2.3 and ADR-0003).

Operated side: when ``operated_side`` is given, ``symmetry_index_operated_pct`` reports
``SI_op = (X_operated - X_contralateral) / (0.5 * (|X_op| + |X_contra|)) * 100``, so a
**positive value means the operated side is larger**.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np

from openacl.schema import Side

from .cycles import GaitCycles
from .spatiotemporal import ALL_PARAMS, Spatiotemporal


def symmetry_index_pct(x_left: float, x_right: float) -> float:
    """Robinson 1987 Symmetry Index in %, positive when the right value is larger."""
    xl, xr = float(x_left), float(x_right)
    if not (np.isfinite(xl) and np.isfinite(xr)):
        return float("nan")
    denominator = 0.5 * (abs(xr) + abs(xl))
    if denominator == 0.0:
        return float("nan")
    return (xr - xl) / denominator * 100.0


def gait_asymmetry_pct(swing_time_left_s: float, swing_time_right_s: float) -> float:
    """Plotnik/Yogev 2007 Gait Asymmetry in %, computed on swing times. Always >= 0."""
    sl, sr = float(swing_time_left_s), float(swing_time_right_s)
    if not (np.isfinite(sl) and np.isfinite(sr)) or sl <= 0 or sr <= 0:
        return float("nan")
    return 100.0 * abs(np.log(sr / sl))


def curve_rms_difference_deg(curve_left: np.ndarray, curve_right: np.ndarray) -> float:
    """RMS difference between two time-normalised curves, in degrees. NaN-aware."""
    left = np.asarray(curve_left, dtype=float)
    right = np.asarray(curve_right, dtype=float)
    if left.shape != right.shape:
        raise ValueError(f"curve shapes differ: {left.shape} vs {right.shape}")
    diff = left - right
    finite = np.isfinite(diff)
    if not finite.any():
        return float("nan")
    return float(np.sqrt(np.mean(diff[finite] ** 2)))


@dataclass(eq=False)
class SymmetryResult:
    """Symmetry measures of one walking pass."""

    symmetry_index_pct: dict[str, float]
    """Robinson SI per spatio-temporal parameter, positive = right larger."""
    symmetry_index_operated_pct: dict[str, float] | None
    """Same values re-signed so that positive = operated side larger. ``None`` if unknown."""
    gait_asymmetry_pct: float
    """Plotnik GA on swing times."""
    curve_rms_diff_deg: dict[str, float]
    """RMS difference of the L/R mean curves per angle channel, in degrees."""
    operated_side: Side | None = None
    sources: dict[str, str] = field(
        default_factory=lambda: {
            "symmetry_index_pct": "Robinson et al. 1987, J Manipulative Physiol Ther 10:172-176",
            "gait_asymmetry_pct": "Yogev/Plotnik et al. 2007, Exp Brain Res 177:336-346",
            "curve_rms_diff_deg": "RMS curve distance, analogous to Baker et al. 2009 GVS",
        }
    )
    warnings: tuple[str, ...] = ()


def compute_symmetry(
    spatiotemporal: Spatiotemporal,
    cycles: GaitCycles | None = None,
    operated_side: Side | None = None,
    *,
    extra_values: Mapping[str, tuple[float, float]] | None = None,
) -> SymmetryResult:
    """Compute SI, GA and curve symmetry from spatio-temporal parameters and cycle curves.

    ``extra_values`` maps a parameter name to ``(left_value, right_value)`` and is appended
    to the SI table, e.g. peak knee flexion derived elsewhere.
    """
    si: dict[str, float] = {}
    for name in ALL_PARAMS:
        left = spatiotemporal.L.get(name)
        right = spatiotemporal.R.get(name)
        if left is None or right is None:
            continue
        si[name] = symmetry_index_pct(left.mean, right.mean)
    for name, (left_value, right_value) in (extra_values or {}).items():
        si[name] = symmetry_index_pct(left_value, right_value)

    ga = gait_asymmetry_pct(spatiotemporal.L.swing_time_s.mean, spatiotemporal.R.swing_time_s.mean)

    curve_rms: dict[str, float] = {}
    warnings: list[str] = []
    if cycles is not None:
        shared = set(cycles.channels("L")) & set(cycles.channels("R"))
        for channel in sorted(shared):
            left = cycles.mean_curve_deg(channel, "L")
            right = cycles.mean_curve_deg(channel, "R")
            if left is None or right is None:
                continue
            curve_rms[channel] = curve_rms_difference_deg(left, right)

    si_operated: dict[str, float] | None = None
    if operated_side is not None:
        # SI is defined right-minus-left; flip the sign when the left side was operated.
        sign = 1.0 if operated_side == "R" else -1.0
        si_operated = {name: sign * value for name, value in si.items()}
        warnings.append(
            "the contralateral limb is not a healthy reference after ACL reconstruction; "
            "limb symmetry can overestimate function (Wellsandt et al. 2017, JOSPT)"
        )

    return SymmetryResult(
        symmetry_index_pct=si,
        symmetry_index_operated_pct=si_operated,
        gait_asymmetry_pct=ga,
        curve_rms_diff_deg=curve_rms,
        operated_side=operated_side,
        warnings=tuple(warnings),
    )

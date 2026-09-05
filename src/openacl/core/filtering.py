"""Zero-phase low-pass filtering of gait time series.

Convention in clinical gait analysis: 4th-order Butterworth low pass with a 6 Hz cut-off,
applied forward and backward (``sosfiltfilt``) so that no phase lag is introduced.
Reference: Winter DA, *Biomechanics and Motor Control of Human Movement*, 4th ed., ch. 3;
6 Hz is the common cut-off for over-ground walking kinematics.

NaN handling (backends emit NaN for undetected frames, see ``openacl.schema``):
- gaps up to ``max_gap_s`` (default 0.25 s) are linearly interpolated and then filtered,
- longer gaps stay NaN and split the signal into segments that are filtered independently,
- leading and trailing gaps are never extrapolated.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfiltfilt

DEFAULT_CUTOFF_HZ = 6.0
DEFAULT_ORDER = 4
DEFAULT_MAX_GAP_S = 0.25


def _contiguous_true(mask: np.ndarray) -> list[tuple[int, int]]:
    """Return ``[(start, end), ...]`` half-open index ranges where ``mask`` is True."""
    if mask.size == 0:
        return []
    d = np.diff(mask.astype(np.int8))
    starts = (np.flatnonzero(d == 1) + 1).tolist()
    ends = (np.flatnonzero(d == -1) + 1).tolist()
    if mask[0]:
        starts.insert(0, 0)
    if mask[-1]:
        ends.append(int(mask.size))
    return list(zip(starts, ends, strict=True))


def interpolate_short_gaps(
    x: np.ndarray, fps: float, max_gap_s: float = DEFAULT_MAX_GAP_S
) -> np.ndarray:
    """Linearly interpolate NaN gaps of at most ``max_gap_s`` seconds.

    Longer gaps and gaps touching the signal borders are left as NaN.
    """
    x = np.asarray(x, dtype=float)
    if x.ndim != 1:
        raise ValueError(f"expected a 1-D signal, got shape {x.shape}")
    out = x.copy()
    finite = np.isfinite(x)
    if not finite.any() or finite.all():
        return out
    max_gap_frames = int(np.floor(max_gap_s * fps))
    idx = np.arange(x.size, dtype=float)
    for start, end in _contiguous_true(~finite):
        if start == 0 or end == x.size:
            continue  # never extrapolate over the borders
        if (end - start) > max_gap_frames:
            continue
        out[start:end] = np.interp(
            idx[start:end], [float(start - 1), float(end)], [x[start - 1], x[end]]
        )
    return out


def _min_length_for(sos: np.ndarray) -> int:
    """Minimum segment length ``sosfiltfilt`` needs with its default padding."""
    return 3 * (2 * len(sos) + 1) + 1


def lowpass(
    x: np.ndarray,
    fps: float,
    cutoff_hz: float = DEFAULT_CUTOFF_HZ,
    order: int = DEFAULT_ORDER,
    max_gap_s: float = DEFAULT_MAX_GAP_S,
) -> np.ndarray:
    """Zero-phase Butterworth low pass of a 1-D signal sampled at ``fps``.

    Short NaN gaps are interpolated first; segments separated by long gaps are filtered
    independently. Segments too short for the filter padding are returned unfiltered.
    """
    x = np.asarray(x, dtype=float)
    if x.ndim != 1:
        raise ValueError(f"expected a 1-D signal, got shape {x.shape}")
    if fps <= 0:
        raise ValueError("fps must be positive")
    nyquist_hz = 0.5 * fps
    if not 0 < cutoff_hz < nyquist_hz:
        raise ValueError(f"cutoff_hz must be in (0, {nyquist_hz}), got {cutoff_hz}")

    filled = interpolate_short_gaps(x, fps, max_gap_s=max_gap_s)
    finite = np.isfinite(filled)
    if not finite.any():
        return filled

    sos = butter(order, cutoff_hz / nyquist_hz, btype="low", output="sos")
    min_len = _min_length_for(sos)
    out = np.full_like(filled, np.nan)
    for start, end in _contiguous_true(finite):
        segment = filled[start:end]
        if segment.size < min_len:
            out[start:end] = segment  # too short to filter without edge artefacts
        else:
            out[start:end] = sosfiltfilt(sos, segment)
    return out


def lowpass_columns(
    a: np.ndarray,
    fps: float,
    cutoff_hz: float = DEFAULT_CUTOFF_HZ,
    order: int = DEFAULT_ORDER,
    max_gap_s: float = DEFAULT_MAX_GAP_S,
) -> np.ndarray:
    """Apply :func:`lowpass` to every column of a ``(n_frames, n_dims)`` array."""
    a = np.asarray(a, dtype=float)
    if a.ndim != 2:
        raise ValueError(f"expected a 2-D array, got shape {a.shape}")
    out = np.empty_like(a, dtype=float)
    for j in range(a.shape[1]):
        out[:, j] = lowpass(a[:, j], fps, cutoff_hz=cutoff_hz, order=order, max_gap_s=max_gap_s)
    return out

"""Tests for the zero-phase Butterworth low pass."""

from __future__ import annotations

import numpy as np
import pytest

from openacl.core.filtering import interpolate_short_gaps, lowpass, lowpass_columns


def _two_tone(fps: float = 200.0, duration_s: float = 5.0):
    t = np.arange(int(fps * duration_s)) / fps
    slow = np.sin(2 * np.pi * 1.0 * t)
    fast = 0.5 * np.sin(2 * np.pi * 20.0 * t)
    return t, slow, slow + fast


def test_lowpass_removes_20hz_and_keeps_1hz():
    _, slow, mixed = _two_tone()
    filtered = lowpass(mixed, fps=200.0, cutoff_hz=6.0, order=4)
    interior = slice(50, -50)
    assert np.max(np.abs(filtered[interior] - slow[interior])) < 0.02
    # the 20 Hz component is attenuated by more than 40 dB
    residual = filtered - slow
    assert np.std(residual[interior]) < 0.01 * np.std(mixed - slow)


def test_lowpass_is_zero_phase():
    """A pure 1 Hz signal must not be shifted in time by the filter."""
    _, slow, _ = _two_tone()
    filtered = lowpass(slow, fps=200.0)
    interior = slice(100, -100)
    lag_correlations = [
        np.corrcoef(np.roll(filtered, k)[interior], slow[interior])[0, 1] for k in (-2, -1, 0, 1, 2)
    ]
    assert int(np.argmax(lag_correlations)) == 2  # best correlation at zero lag


def test_short_gaps_are_interpolated_long_gaps_stay_nan():
    fps = 60.0
    x = np.arange(600, dtype=float)
    x[100:110] = np.nan  # 10 frames = 0.167 s -> interpolated
    x[300:330] = np.nan  # 30 frames = 0.5 s   -> stays NaN
    filled = interpolate_short_gaps(x, fps, max_gap_s=0.25)
    assert np.allclose(filled[100:110], np.arange(100, 110))
    assert np.isnan(filled[300:330]).all()


def test_leading_and_trailing_gaps_are_not_extrapolated():
    x = np.arange(100, dtype=float)
    x[:3] = np.nan
    x[-3:] = np.nan
    filled = interpolate_short_gaps(x, 60.0)
    assert np.isnan(filled[:3]).all()
    assert np.isnan(filled[-3:]).all()


def test_lowpass_filters_segments_around_a_long_gap():
    fps = 100.0
    t = np.arange(1000) / fps
    x = np.sin(2 * np.pi * 1.0 * t) + 0.5 * np.sin(2 * np.pi * 25.0 * t)
    x[400:500] = np.nan  # 1 s gap
    filtered = lowpass(x, fps)
    assert np.isnan(filtered[400:500]).all()
    for segment in (slice(50, 350), slice(550, 950)):
        assert np.max(np.abs(filtered[segment] - np.sin(2 * np.pi * t[segment]))) < 0.05


def test_lowpass_rejects_cutoff_above_nyquist():
    with pytest.raises(ValueError):
        lowpass(np.zeros(100), fps=10.0, cutoff_hz=6.0)


def test_lowpass_all_nan_returns_all_nan():
    out = lowpass(np.full(200, np.nan), fps=60.0)
    assert np.isnan(out).all()


def test_lowpass_columns_matches_per_column_lowpass():
    t = np.arange(400) / 100.0
    a = np.column_stack([np.sin(2 * np.pi * t), np.cos(2 * np.pi * 3 * t)])
    out = lowpass_columns(a, fps=100.0)
    assert out.shape == a.shape
    assert np.allclose(out[:, 0], lowpass(a[:, 0], 100.0))

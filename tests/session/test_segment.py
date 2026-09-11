"""Tests for :mod:`openacl.session.segment` (ADR-0010).

The pure detection logic (:func:`find_passes`) is tested against synthetic foreground
area/centroid time series, no ``ffmpeg`` involved. The ffmpeg-backed pieces
(:func:`decode_grayscale`, :func:`segment_video` end to end) are gated behind
``shutil.which("ffmpeg")`` and generate their own tiny synthetic video with ffmpeg's ``lavfi``
source, so they need no checked-in video fixture.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
import yaml

from openacl.session.segment import (
    MAX_GAP_S,
    MIN_DRIFT_PX,
    MIN_PASS_AREA_FRACTION,
    MIN_PASS_DURATION_S,
    PASS_PAD_S,
    decode_grayscale,
    find_passes,
    segment_video,
)

DT_S = 1.0 / 10.0  # matches PROBE_FPS
AREA_PRESENT = 0.05  # > MIN_PASS_AREA_FRACTION
AREA_ABSENT = 0.0


def _segment(duration_s: float, cx_start: float, cx_end: float, area: float = AREA_PRESENT):
    n = round(duration_s / DT_S)
    return np.full(n, area), np.linspace(cx_start, cx_end, n)


def _baseline(duration_s: float):
    n = round(duration_s / DT_S)
    return np.full(n, AREA_ABSENT), np.full(n, np.nan)


def _build_timeline(
    *segments: tuple[np.ndarray, np.ndarray],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    area = np.concatenate([s[0] for s in segments])
    cx = np.concatenate([s[1] for s in segments])
    t_s = np.arange(area.size) * DT_S
    return t_s, area, cx


def test_two_passes_in_opposite_directions_are_found() -> None:
    t_s, area, cx = _build_timeline(
        _baseline(1.0),
        _segment(4.0, 50.0, 250.0),  # +x
        _baseline(1.0),
        _segment(4.0, 250.0, 50.0),  # -x
        _baseline(1.0),
    )
    passes = find_passes(t_s, area, cx)
    assert [p.direction for p in passes] == ["+x", "-x"]
    for p in passes:
        assert p.duration_s >= MIN_PASS_DURATION_S
        assert abs(p.drift_px) >= MIN_DRIFT_PX


def test_too_short_run_is_rejected() -> None:
    short_duration = MIN_PASS_DURATION_S - 1.0
    t_s, area, cx = _build_timeline(
        _baseline(1.0),
        _segment(short_duration, 50.0, 250.0),
        _baseline(1.0),
    )
    passes = find_passes(t_s, area, cx)
    assert passes == []


def test_run_without_drift_is_ignored() -> None:
    # Present long enough, but the centroid barely moves (e.g. standing still, turning around).
    rng = np.random.default_rng(0)
    n = round(4.0 / DT_S)
    area = np.full(n, AREA_PRESENT)
    cx = 150.0 + rng.uniform(-5.0, 5.0, size=n)
    t_s = np.arange(n) * DT_S
    passes = find_passes(t_s, area, cx)
    assert passes == []


def test_short_gap_is_bridged_into_one_pass() -> None:
    gap_s = MAX_GAP_S - 0.1
    assert gap_s > 0
    t_s, area, cx = _build_timeline(
        _baseline(1.0),
        _segment(2.0, 50.0, 140.0),
        _baseline(gap_s),
        _segment(2.0, 160.0, 250.0),
        _baseline(1.0),
    )
    passes = find_passes(t_s, area, cx)
    assert len(passes) == 1
    # The bridged run spans both sub-runs and the gap, well above the raw 2 s parts alone.
    assert passes[0].duration_s > 2.0 + gap_s
    assert passes[0].direction == "+x"
    assert passes[0].drift_px >= MIN_DRIFT_PX


def test_gap_longer_than_threshold_is_not_bridged() -> None:
    gap_s = MAX_GAP_S + 0.3
    t_s, area, cx = _build_timeline(
        _baseline(1.0),
        _segment(2.0, 50.0, 140.0),
        _baseline(gap_s),
        _segment(2.0, 160.0, 250.0),
        _baseline(1.0),
    )
    passes = find_passes(t_s, area, cx)
    # Each 2 s sub-run alone is below MIN_PASS_DURATION_S, so neither survives.
    assert passes == []


def test_pass_padding_extends_the_cut_window() -> None:
    t_s, area, cx = _build_timeline(
        _baseline(1.0),
        _segment(4.0, 50.0, 250.0),
        _baseline(1.0),
    )
    passes = find_passes(t_s, area, cx)
    assert len(passes) == 1
    p = passes[0]
    assert p.t_start_s == pytest.approx(1.0 - PASS_PAD_S, abs=1e-6)
    assert p.t_end_s == pytest.approx(4.9 + PASS_PAD_S, abs=1e-6)


def test_min_area_threshold_constant_matches_adr_0010() -> None:
    assert MIN_PASS_AREA_FRACTION == pytest.approx(0.010)


# -------------------------------------------------------------------- ffmpeg-dependent tests

pytestmark_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not on PATH")


def test_decode_grayscale_raises_without_ffmpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    with pytest.raises(RuntimeError, match="ffmpeg"):
        decode_grayscale(Path("does-not-matter.mp4"))


@pytest.fixture
def synthetic_walk_video(tmp_path: Path) -> Path:
    """A 6 s, 320x180 black video with a white box crossing left to right from t=1 to t=5 s.

    Built with ffmpeg's ``lavfi`` source directly (no checked-in binary fixture). Uses
    ``overlay`` (not ``drawbox``) for the moving box: this ffmpeg build evaluates ``drawbox``'s
    ``x``/``y`` expressions once at init (no ``eval=frame`` option available), so a ``t``-based
    position there silently resolves to an out-of-frame constant; ``overlay`` re-evaluates its
    ``x``/``y`` expressions every frame natively.
    """
    ffmpeg = shutil.which("ffmpeg")
    assert ffmpeg is not None
    video = tmp_path / "walk.mp4"
    cmd = [
        ffmpeg,
        "-v",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=320x180:d=6:r=30",
        "-f",
        "lavfi",
        "-i",
        "color=c=white:s=30x90:d=6:r=30",
        "-filter_complex",
        "[0:v][1:v]overlay=x='20+(t-1)*57.5':y=45:enable='between(t,1,5)'",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(video),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return video


@pytestmark_ffmpeg
def test_decode_grayscale_shape(synthetic_walk_video: Path) -> None:
    frames = decode_grayscale(synthetic_walk_video)
    assert frames.dtype == np.uint8
    # ~6 s at PROBE_FPS=10 -> ~60 frames.
    assert 55 <= frames.shape[0] <= 65
    assert frames.shape[1:] == (180, 320)


@pytestmark_ffmpeg
def test_segment_video_dry_run_detects_one_pass(synthetic_walk_video: Path) -> None:
    passes = segment_video(synthetic_walk_video, Path("unused"), dry_run=True)
    assert len(passes) == 1
    p = passes[0]
    assert p.direction == "+x"
    assert 3.0 <= p.duration_s <= 4.6
    assert p.file is None


@pytestmark_ffmpeg
def test_segment_video_cuts_clip_and_writes_passes_yaml(
    synthetic_walk_video: Path, tmp_path: Path
) -> None:
    out_dir = tmp_path / "session"
    passes = segment_video(synthetic_walk_video, out_dir, condition="socken")
    assert len(passes) == 1
    assert passes[0].file == "A_pass01.mp4"
    clip = out_dir / "A_pass01.mp4"
    assert clip.exists()
    assert clip.stat().st_size > 0

    passes_yaml = yaml.safe_load((out_dir / "passes.yaml").read_text())
    assert len(passes_yaml) == 1
    assert passes_yaml[0]["file"] == "A_pass01.mp4"
    assert passes_yaml[0]["direction"] == "+x"

    meta = yaml.safe_load((out_dir / "meta.yaml").read_text())
    assert meta["condition"] == "socken"
    assert meta["source_video"] == synthetic_walk_video.name


@pytestmark_ffmpeg
def test_segment_video_rerun_reuses_existing_clip(
    synthetic_walk_video: Path, tmp_path: Path
) -> None:
    out_dir = tmp_path / "session"
    segment_video(synthetic_walk_video, out_dir)
    clip = out_dir / "A_pass01.mp4"
    first_mtime = clip.stat().st_mtime_ns
    segment_video(synthetic_walk_video, out_dir)
    assert clip.stat().st_mtime_ns == first_mtime

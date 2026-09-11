"""Pass segmentation: one long, static-camera video -> per-pass clips (ADR-0010).

The recording protocol (``docs/PROTOKOLL-AUFNAHME.md``) originally asked for one short video
per pass (``A_pass01.mov`` ...). In practice it is easier to let the camera run continuously
while walking back and forth 10 to 20 times. This module finds the individual passes in that
long video from motion alone (no pose model) and cuts them into the ``A_pass<NN>.mp4`` files
the session layer (``openacl.session.model``) expects, plus a ``passes.yaml`` that records each
pass's time window, walking direction and centroid drift.

Detection has two stages, kept separate so the pure segmentation logic (:func:`find_passes`) is
testable without ``ffmpeg`` or a real video:

1. :func:`decode_grayscale` decodes the video via ``ffmpeg`` to a small grayscale raw stream
   (:data:`PROBE_WIDTH_PX` x :data:`PROBE_HEIGHT_PX` at :data:`PROBE_FPS`) and
   :func:`foreground_timeseries` turns each frame into a foreground area fraction and an x
   centroid, against a median background computed over :data:`BACKGROUND_SAMPLE_FRAMES` frames
   spread evenly over the video (the walker is absent from most frames, so the per-pixel median
   is the empty background).
2. :func:`find_passes` turns the ``(t_s, area_frac, cx_px)`` time series into a list of
   :class:`Pass` objects: a contiguous run of foreground area above
   :data:`MIN_PASS_AREA_FRACTION` (short gaps up to :data:`MAX_GAP_S` are bridged) that lasts at
   least :data:`MIN_PASS_DURATION_S` and whose centroid drifts by at least :data:`MIN_DRIFT_PX`
   between its first and last quarter -- this drift requirement is what rejects someone standing
   still, turning around, or adjusting the camera at the edge of frame.

:func:`segment_video` orchestrates both stages, cuts each pass frame-exactly with ``ffmpeg``
(0.15 s lead-in/out, H.264/yuv420p, no audio), and writes ``passes.yaml`` plus a ``meta.yaml``
copied from the source session folder with ``condition`` and ``source_video`` added.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

import numpy as np
import yaml

Direction = Literal["+x", "-x"]

# -- stage 1: motion probe -----------------------------------------------------------------
PROBE_WIDTH_PX = 320
PROBE_HEIGHT_PX = 180
PROBE_FPS = 10.0
"""Decoding resolution/rate for motion detection; plenty for a foreground blob, cheap to decode."""

BACKGROUND_SAMPLE_FRAMES = 200
"""Number of evenly spaced frames used to build the median background."""

FOREGROUND_DIFF_THRESHOLD = 25
"""Grayscale intensity difference from the background above which a pixel counts as foreground."""

# -- stage 2: pass detection ----------------------------------------------------------------
MIN_PASS_AREA_FRACTION = 0.010
"""Foreground area, as a fraction of the probe frame, above which the walker is 'in the picture'."""

MIN_PASS_DURATION_S = 3.0
"""Shortest contiguous run (before lead-in/out padding) that counts as a pass."""

MAX_GAP_S = 0.5
"""Foreground dropouts up to this long (e.g. a missed frame) are bridged within one run."""

MIN_DRIFT_PX = 120.0
"""Minimum centroid drift between the first and last quarter of a run; rejects standing still,
turning around, or camera adjustment at the edge of the frame."""

PASS_PAD_S = 0.15
"""Lead-in/out kept on each cut clip so the first/last heel strike is not cropped off."""

# -- stage 3: cutting -------------------------------------------------------------------------
CUT_CRF = 18
"""libx264 constant-rate-factor for the re-encoded per-pass clips."""

PASSES_FILENAME = "passes.yaml"
META_FILENAME = "meta.yaml"


def _require_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError(
            "ffmpeg is not installed or not on PATH. Install it with `brew install ffmpeg` "
            "(macOS) and retry."
        )
    return ffmpeg


@dataclass(frozen=True)
class Pass:
    """One detected walking pass in the source video's time base."""

    t_start_s: float
    """Start of the cut window, including :data:`PASS_PAD_S` lead-in."""
    t_end_s: float
    """End of the cut window, including :data:`PASS_PAD_S` trail-out."""
    duration_s: float
    """Duration of the detected motion run itself, *without* the padding."""
    direction: Direction
    drift_px: float
    """Median centroid drift between the run's last and first quarter, signed."""
    mean_area: float
    """Mean foreground area fraction over the run."""
    file: str | None = None
    """Set by :func:`cut_passes` once the clip has been written."""

    def as_dict(self) -> dict:
        return {
            "t_start_s": round(self.t_start_s, 2),
            "t_end_s": round(self.t_end_s, 2),
            "duration_s": round(self.duration_s, 2),
            "direction": self.direction,
            "drift_px": round(self.drift_px, 1),
            "mean_area": round(self.mean_area, 4),
            "file": self.file,
        }


def decode_grayscale(
    video: Path | str,
    *,
    width: int = PROBE_WIDTH_PX,
    height: int = PROBE_HEIGHT_PX,
    fps: float = PROBE_FPS,
) -> np.ndarray:
    """Decode ``video`` to grayscale frames of shape ``(n_frames, height, width)``, ``uint8``.

    Raises ``RuntimeError`` if ``ffmpeg`` is not on ``PATH`` (see
    :func:`openacl.backends.video.transcode_to_h264` for the same pattern), or if ffmpeg itself
    fails (e.g. an unreadable container).
    """
    ffmpeg = _require_ffmpeg()
    video = Path(video)
    cmd = [
        ffmpeg,
        "-v",
        "error",
        "-i",
        str(video),
        "-vf",
        f"fps={fps},scale={width}:{height}",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "gray",
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg could not decode {video} for motion probing (exit {result.returncode}):\n"
            f"{result.stderr[-4000:].decode(errors='replace')}"
        )
    raw = result.stdout
    frame_bytes = width * height
    n = len(raw) // frame_bytes
    if n == 0:
        raise RuntimeError(f"ffmpeg produced no frames while probing {video}")
    return np.frombuffer(raw, dtype=np.uint8)[: n * frame_bytes].reshape(n, height, width)


def foreground_timeseries(
    frames: np.ndarray,
    *,
    fps: float = PROBE_FPS,
    background_sample_frames: int = BACKGROUND_SAMPLE_FRAMES,
    diff_threshold: int = FOREGROUND_DIFF_THRESHOLD,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-frame foreground area fraction and x centroid against a median background.

    Returns ``(t_s, area_frac, cx_px)``, each shape ``(n_frames,)``. ``cx_px`` is ``NaN`` for a
    frame with no foreground pixels above ``diff_threshold``.
    """
    frames = frames.astype(np.int16)
    n_frames, _height, width = frames.shape
    stride = max(1, n_frames // max(1, background_sample_frames))
    background = np.median(frames[::stride], axis=0)

    t_s = np.arange(n_frames, dtype=float) / fps
    area_frac = np.empty(n_frames, dtype=float)
    cx_px = np.empty(n_frames, dtype=float)
    x_coords = np.arange(width, dtype=float)
    for k in range(n_frames):
        mask = np.abs(frames[k] - background) > diff_threshold
        area_frac[k] = mask.mean()
        columns = mask.sum(axis=0)
        total = columns.sum()
        cx_px[k] = float((columns * x_coords).sum() / total) if total > 0 else float("nan")
    return t_s, area_frac, cx_px


def _bridge_runs(mask: np.ndarray, t_s: np.ndarray, max_gap_s: float) -> list[tuple[int, int]]:
    """Contiguous runs of ``True`` in ``mask``, bridging gaps of at most ``max_gap_s``.

    Returns ``(start_index, end_index)`` pairs, inclusive, into ``t_s``.
    """
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []
    runs: list[list[int]] = [[int(idx[0]), int(idx[0])]]
    for i in idx[1:]:
        i = int(i)
        if t_s[i] - t_s[runs[-1][1]] <= max_gap_s:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    return [(a, b) for a, b in runs]


def find_passes(
    t_s: np.ndarray,
    area_frac: np.ndarray,
    cx_px: np.ndarray,
    *,
    min_area_fraction: float = MIN_PASS_AREA_FRACTION,
    min_duration_s: float = MIN_PASS_DURATION_S,
    max_gap_s: float = MAX_GAP_S,
    min_drift_px: float = MIN_DRIFT_PX,
    pad_s: float = PASS_PAD_S,
) -> list[Pass]:
    """Turn a foreground motion time series into a list of detected passes.

    Pure function, no I/O: this is what the synthetic tests exercise directly.
    """
    t_s = np.asarray(t_s, dtype=float)
    area_frac = np.asarray(area_frac, dtype=float)
    cx_px = np.asarray(cx_px, dtype=float)
    mask = area_frac > min_area_fraction

    passes: list[Pass] = []
    for start, end in _bridge_runs(mask, t_s, max_gap_s):
        t0, t1 = float(t_s[start]), float(t_s[end])
        if t1 - t0 < min_duration_s:
            continue
        window = (t_s >= t0) & (t_s <= t1) & np.isfinite(cx_px)
        if window.sum() < 4:
            continue
        c = cx_px[window]
        quarter = max(1, c.size // 4)
        drift = float(np.median(c[-quarter:]) - np.median(c[:quarter]))
        if abs(drift) < min_drift_px:
            continue
        passes.append(
            Pass(
                t_start_s=max(0.0, t0 - pad_s),
                t_end_s=t1 + pad_s,
                duration_s=t1 - t0,
                direction="+x" if drift > 0 else "-x",
                drift_px=drift,
                mean_area=float(area_frac[window].mean()),
            )
        )
    return passes


def cut_passes(
    video: Path | str,
    passes: list[Pass],
    out_dir: Path | str,
    *,
    camera: str = "A",
    crf: int = CUT_CRF,
) -> list[Pass]:
    """Cut each pass out of ``video`` with ``ffmpeg`` into ``<camera>_pass<NN>.mp4``.

    Returns new :class:`Pass` objects with ``file`` set; existing target files are kept as-is
    (re-running a segmentation does not re-encode clips that are already there).
    """
    ffmpeg = _require_ffmpeg()
    video = Path(video)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cut: list[Pass] = []
    for k, p in enumerate(passes, start=1):
        name = f"{camera}_pass{k:02d}.mp4"
        dst = out_dir / name
        if not dst.exists():
            cmd = [
                ffmpeg,
                "-v",
                "error",
                "-y",
                "-ss",
                str(p.t_start_s),
                "-to",
                str(p.t_end_s),
                "-i",
                str(video),
                "-c:v",
                "libx264",
                "-crf",
                str(crf),
                "-pix_fmt",
                "yuv420p",
                "-an",
                str(dst),
            ]
            result = subprocess.run(cmd, capture_output=True, check=False)
            if result.returncode != 0:
                raise RuntimeError(
                    f"ffmpeg could not cut pass {k} ({p.t_start_s:.2f}-{p.t_end_s:.2f} s) from "
                    f"{video} (exit {result.returncode}):\n"
                    f"{result.stderr[-4000:].decode(errors='replace')}"
                )
        cut.append(replace(p, file=name))
    return cut


def _write_meta(out_dir: Path, meta_src: Path | None, condition: str | None, video: Path) -> None:
    meta: dict = {}
    if meta_src is not None and meta_src.exists():
        loaded = yaml.safe_load(meta_src.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            meta = loaded
    if condition is not None:
        meta["condition"] = condition
    meta["source_video"] = video.name
    note = f"Passes auto-segmented from {video.name} (openacl segment, ADR-0010)."
    meta["notes"] = f"{meta.get('notes') or ''} {note}".strip()
    (out_dir / META_FILENAME).write_text(
        yaml.safe_dump(meta, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def segment_video(
    video: Path | str,
    out_dir: Path | str,
    *,
    meta_src: Path | str | None = None,
    condition: str | None = None,
    camera: str = "A",
    dry_run: bool = False,
) -> list[Pass]:
    """Detect and (unless ``dry_run``) cut the passes of a long, static-camera ``video``.

    Writes ``<out_dir>/passes.yaml`` and, when a source ``meta.yaml`` is available (or a
    ``condition`` is given), ``<out_dir>/meta.yaml`` with ``condition`` and ``source_video``
    added (ADR-0010). ``dry_run=True`` only returns the detected passes, without touching the
    filesystem beyond decoding the video.
    """
    video = Path(video)
    out_dir = Path(out_dir)

    frames = decode_grayscale(video)
    t_s, area_frac, cx_px = foreground_timeseries(frames)
    passes = find_passes(t_s, area_frac, cx_px)

    if dry_run:
        return passes

    out_dir.mkdir(parents=True, exist_ok=True)
    cut = cut_passes(video, passes, out_dir, camera=camera)
    (out_dir / PASSES_FILENAME).write_text(
        yaml.safe_dump([p.as_dict() for p in cut], sort_keys=False), encoding="utf-8"
    )
    meta_path = Path(meta_src) if meta_src is not None else None
    if meta_path is not None or condition is not None:
        _write_meta(out_dir, meta_path, condition, video)
    return cut

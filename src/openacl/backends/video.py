"""Video probing and optional transcoding helpers, backend-independent.

``probe`` reads container/stream metadata with OpenCV so callers can warn about low frame
rates or portrait orientation before running a kinematics backend on the file.

iPhones commonly record HEVC (H.265) in a ``.mov`` container. Whether OpenCV can decode that
depends on the FFmpeg build linked into the installed ``opencv-python`` wheel; ``probe`` does
not itself try to read frames, only container metadata, so it succeeds even when the codec
cannot be decoded. Use :func:`can_decode` to check that a video's frames are actually readable,
and :func:`transcode_to_h264` (needs the ``ffmpeg`` binary on ``PATH``) as a fallback.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import cv2

MIN_RECOMMENDED_FPS = 50.0
"""Below this, fast swing-phase knee motion is under-sampled for angle-velocity estimates."""


@dataclass(frozen=True)
class VideoInfo:
    """Container/stream metadata for one video file."""

    path: Path
    fps: float
    width: int
    height: int
    n_frames: int
    duration_s: float
    codec: str
    """Four-character code (fourcc) reported by the container, e.g. ``"hvc1"``, ``"avc1"``."""
    warnings: tuple[str, ...] = ()


def _fourcc_to_str(fourcc: float) -> str:
    code = int(fourcc)
    chars = "".join(chr((code >> 8 * i) & 0xFF) for i in range(4))
    return chars.strip()


def probe(video: Path | str) -> VideoInfo:
    """Read container/stream metadata for ``video`` with OpenCV.

    Raises ``FileNotFoundError`` if the file cannot be opened at all (missing file or codec
    OpenCV's backend cannot even parse the container for).
    """
    video = Path(video)
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        cap.release()
        raise FileNotFoundError(f"Could not open video: {video}")

    fps = float(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    codec = _fourcc_to_str(cap.get(cv2.CAP_PROP_FOURCC))
    cap.release()

    duration_s = n_frames / fps if fps > 0 else float("nan")

    warnings: list[str] = []
    if fps <= 0:
        warnings.append(
            "fps could not be read from the container; downstream code must not assume it"
        )
    elif fps < MIN_RECOMMENDED_FPS:
        warnings.append(
            f"fps={fps:.1f} is below the recommended {MIN_RECOMMENDED_FPS:.0f} fps for gait "
            "angle-velocity estimates; consider a higher frame rate capture"
        )
    if height > width:
        warnings.append(
            f"portrait orientation ({width}x{height}); Sports2D expects a landscape, sagittal "
            "view of the full body"
        )

    return VideoInfo(
        path=video,
        fps=fps,
        width=width,
        height=height,
        n_frames=n_frames,
        duration_s=duration_s,
        codec=codec,
        warnings=tuple(warnings),
    )


def can_decode(video: Path | str, n_probe_frames: int = 5) -> bool:
    """Try to actually read a few frames; ``probe`` alone only reads container metadata."""
    video = Path(video)
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        cap.release()
        return False
    ok = True
    for _ in range(n_probe_frames):
        read_ok, frame = cap.read()
        if not read_ok or frame is None:
            ok = False
            break
    cap.release()
    return ok


def transcode_to_h264(src: Path | str, dst: Path | str, *, crf: int = 18) -> Path:
    """Re-encode ``src`` to H.264/yuv420p at ``dst`` with ``ffmpeg``.

    Use this when :func:`can_decode` fails on a video (e.g. an HEVC ``.mov`` OpenCV's FFmpeg
    build cannot decode). Requires the ``ffmpeg`` binary on ``PATH`` (``brew install ffmpeg``
    on macOS); raises ``RuntimeError`` with a clear message if it is missing, rather than a
    raw ``FileNotFoundError`` from ``subprocess``.
    """
    src = Path(src)
    dst = Path(dst)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError(
            "ffmpeg is not installed or not on PATH. Install it with `brew install ffmpeg` "
            "(macOS) and retry, or use a video OpenCV can already decode "
            "(see openacl.backends.video.can_decode)."
        )
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(src),
        "-c:v",
        "libx264",
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        str(dst),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg transcode failed (exit {result.returncode}) for {src} -> {dst}:\n"
            f"{result.stderr[-4000:]}"
        )
    return dst

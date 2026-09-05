"""Minimal, dependency-light parsers for the ``.trc`` (pose) and ``.mot`` (angles) files that
Sports2D writes (OpenSim-compatible text formats). No pickle, no pandas: plain text parsing
with ``numpy`` for the numeric arrays, so tiny hand-written fixtures are easy to test against.

TRC layout (see ``Sports2D.process.make_trc_with_trc_data``)::

    PathFileType\t4\t(X/Y/Z)\t<path>
    DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\tOrigDataRate\tOrigDataStartFrame\tOrigNumFrames
    <values for the row above, tab-separated>
    Frame#\tTime\t<marker1>\t\t\t<marker2>\t\t\t...\t\t\t
    \t\tX1\tY1\tZ1\tX2\tY2\tZ2...
    <frame_idx>\t<time_s>\t<X1>\t<Y1>\t<Z1>\t<X2>\t<Y2>\t<Z2>\t...
    ...

MOT layout (see ``Sports2D.process.make_mot_with_angles``)::

    Coordinates
    version=1
    nRows=<n>
    nColumns=<n>
    inDegrees=yes
    <blank>
    Units are S.I. units (second, meters, Newtons, ...)
    If the header above contains a line with 'inDegrees', ...
    <blank>
    endheader
    time\t<angle1>\t<angle2>\t...
    <time_s>\t<value1>\t<value2>\t...
    ...

Both formats write missing values as empty tab-separated fields (pandas ``to_csv`` default for
``NaN``); this module reads an empty field back as ``np.nan``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class TrcData:
    """Parsed ``.trc`` pose file."""

    fps: float
    units: str
    """``"m"`` or ``"mm"`` as written in the file header; note Sports2D always writes ``"m"``
    even for pixel-unit (``_px``) files, so callers must not trust this field to distinguish
    pixels from metres -- use the file name (``_px_`` vs ``_m_``) or the caller's own config."""
    time_s: np.ndarray
    """Shape ``(n_frames,)``."""
    markers: dict[str, np.ndarray]
    """Marker name -> array of shape ``(n_frames, 3)`` (X, Y, Z columns as written)."""


@dataclass(frozen=True)
class MotData:
    """Parsed ``.mot`` angles file."""

    time_s: np.ndarray
    """Shape ``(n_frames,)``."""
    angles: dict[str, np.ndarray]
    """Angle name (as written, e.g. ``"right knee"``) -> array of shape ``(n_frames,)``."""


def _to_float(token: str) -> float:
    token = token.strip()
    if token == "":
        return float("nan")
    return float(token)


def read_trc(path: Path | str) -> TrcData:
    """Parse a Sports2D ``.trc`` pose file."""
    path = Path(path)
    lines = path.read_text().splitlines()
    if len(lines) < 5:
        raise ValueError(f"{path}: not enough lines for a .trc file")

    labels = lines[1].split("\t")
    values = lines[2].split("\t")
    header = dict(zip(labels, values, strict=False))
    fps = float(header["DataRate"])
    units = header.get("Units", "")

    marker_row = lines[3].split("\t")[2:]  # drop "Frame#", "Time"
    marker_names = [name for name in marker_row if name.strip() != ""]

    data_lines = [line for line in lines[5:] if line.strip() != ""]
    n_frames = len(data_lines)
    n_markers = len(marker_names)

    time_s = np.empty(n_frames, dtype=float)
    coords = np.full((n_frames, n_markers, 3), np.nan, dtype=float)
    for row_idx, line in enumerate(data_lines):
        fields = line.split("\t")
        # fields[0] = frame index, fields[1] = time, then 3 columns per marker
        time_s[row_idx] = _to_float(fields[1])
        values_part = fields[2:]
        for m in range(n_markers):
            base = m * 3
            if base + 2 >= len(values_part):
                break
            coords[row_idx, m, 0] = _to_float(values_part[base])
            coords[row_idx, m, 1] = _to_float(values_part[base + 1])
            coords[row_idx, m, 2] = _to_float(values_part[base + 2])

    markers = {name: coords[:, i, :] for i, name in enumerate(marker_names)}
    return TrcData(fps=fps, units=units, time_s=time_s, markers=markers)


def read_mot(path: Path | str) -> MotData:
    """Parse a Sports2D ``.mot`` angles file."""
    path = Path(path)
    lines = path.read_text().splitlines()
    try:
        header_idx = lines.index("endheader")
    except ValueError as exc:
        raise ValueError(f"{path}: no 'endheader' line found") from exc

    column_line = lines[header_idx + 1]
    columns = column_line.split("\t")
    angle_names = columns[1:]  # drop "time"

    data_lines = [line for line in lines[header_idx + 2 :] if line.strip() != ""]
    n_frames = len(data_lines)
    n_angles = len(angle_names)

    time_s = np.empty(n_frames, dtype=float)
    values = np.full((n_frames, n_angles), np.nan, dtype=float)
    for row_idx, line in enumerate(data_lines):
        fields = line.split("\t")
        time_s[row_idx] = _to_float(fields[0])
        for a in range(n_angles):
            col = a + 1
            if col < len(fields):
                values[row_idx, a] = _to_float(fields[col])

    angles = {name: values[:, i] for i, name in enumerate(angle_names)}
    return MotData(time_s=time_s, angles=angles)

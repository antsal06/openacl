"""Pose/angle time alignment of the Sports2D adapter (the ``to_meters=True`` path).

With ``to_meters=True`` Sports2D writes the metre ``.trc`` only for the frames whose
pixel-to-metre conversion it could solve (measured on the bundled demo video: 160 of 230
frames), while the ``.mot`` angle file keeps the full video time base. The adapter puts the
pose back on the angle time axis instead of refusing the run.
"""

from __future__ import annotations

import numpy as np
import pytest

from openacl.backends._trc_mot import TrcData
from openacl.backends.sports2d import align_markers_to_time

FPS = 30.0


def _trc(start_frame: int, n_frames: int) -> TrcData:
    time_s = (np.arange(n_frames) + start_frame) / FPS
    markers = {
        "RHeel": np.column_stack(
            [np.arange(n_frames, dtype=float), np.zeros(n_frames), np.zeros(n_frames)]
        )
    }
    return TrcData(fps=FPS, units="m", time_s=time_s, markers=markers)


def test_trimmed_pose_is_padded_with_nan() -> None:
    master = np.arange(230, dtype=float) / FPS
    aligned = align_markers_to_time(_trc(start_frame=42, n_frames=160), master)

    heel = aligned["RHeel"]
    assert heel.shape == (230, 3)
    assert np.isnan(heel[:42]).all()
    assert np.isnan(heel[202:]).all()
    assert np.isfinite(heel[42:202]).all()
    # the values keep their order, they are only shifted
    assert heel[42, 0] == pytest.approx(0.0)
    assert heel[201, 0] == pytest.approx(159.0)


def test_untrimmed_pose_is_returned_unchanged() -> None:
    master = np.arange(50, dtype=float) / FPS
    aligned = align_markers_to_time(_trc(start_frame=0, n_frames=50), master)
    assert np.isfinite(aligned["RHeel"]).all()
    assert aligned["RHeel"][:, 0] == pytest.approx(np.arange(50, dtype=float))


def test_pose_reaching_past_the_angle_axis_is_clipped() -> None:
    master = np.arange(50, dtype=float) / FPS
    aligned = align_markers_to_time(_trc(start_frame=40, n_frames=30), master)
    heel = aligned["RHeel"]
    assert heel.shape == (50, 3)
    assert np.isfinite(heel[40:50]).all()
    assert np.isnan(heel[:40]).all()


def test_disjoint_time_axes_raise() -> None:
    master = np.arange(50, dtype=float) / FPS
    with pytest.raises(ValueError, match="do not overlap"):
        align_markers_to_time(_trc(start_frame=500, n_frames=10), master)


def test_a_one_frame_angle_file_raises() -> None:
    with pytest.raises(ValueError, match="fewer than two frames"):
        align_markers_to_time(_trc(start_frame=0, n_frames=5), np.array([0.0]))

"""Tests for :mod:`openacl.backends.opencap` (ADR-0011), against tiny synthetic ``.mot``/``.trc``
fixtures written in the same OpenSim-compatible text format :mod:`openacl.backends._trc_mot`
parses for Sports2D (see ``tests/backends/test_trc_mot.py`` for the real-file version of this
format).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from openacl.backends.opencap import load_opencap
from openacl.schema import ANGLE_CHANNELS

N_FRAMES = 6
FPS = 30.0
DT_S = 1.0 / FPS

MARKER_NAMES = (
    "midHip",
    "RHip",
    "LHip",
    "RKnee",
    "LKnee",
    "RAnkle",
    "LAnkle",
    "RHeel",
    "LHeel",
    "RBigToe",
    "LBigToe",
    "RSmallToe",
    "LSmallToe",
    "RShoulder",
    "LShoulder",
)

MOT_COLUMNS = {
    "knee_angle_r": [10.0, 20.0, 0.0, 40.0, 50.0, 60.0],  # clip at idx 2
    "knee_angle_l": [15.0, 25.0, 35.0, 45.0, 55.0, 65.0],
    "hip_flexion_r": [-10.0, -15.0, -20.0, -25.0, -22.0, -18.0],
    "hip_flexion_l": [-5.0, -10.0, -20.0, -30.0, -25.0, -22.0],  # clip at idx 3
    "ankle_angle_r": [-50.0, -40.0, -30.0, -20.0, -10.0, 0.0],  # clip at idx 0
    "ankle_angle_l": [-45.0, -35.0, -25.0, -15.0, -5.0, 5.0],
    "pelvis_tilt": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
    "pelvis_list": [0.5, 1.5, -0.5, -1.5, 2.5, -2.5],
    "hip_adduction_r": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
    "hip_adduction_l": [-1.0, -2.0, -3.0, -4.0, -5.0, -6.0],
    "hip_rotation_r": [2.0, 4.0, 6.0, 8.0, 10.0, 12.0],
    "hip_rotation_l": [-2.0, -4.0, -6.0, -8.0, -10.0, -12.0],
}


def _write_trc(path: Path, markers: dict[str, np.ndarray], n_frames: int) -> None:
    names = list(markers)
    time_s = np.arange(n_frames) * DT_S
    lines = [
        f"PathFileType\t4\t(X/Y/Z)\t{path}",
        "DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\tOrigDataRate\tOrigDataStartFrame\tOrigNumFrames",
        f"{FPS}\t{FPS}\t{n_frames}\t{len(names)}\tm\t{FPS}\t0\t{n_frames}",
        "Frame#\tTime\t" + "".join(f"{name}\t\t\t" for name in names),
        "\t\t" + "\t".join(f"{axis}{i + 1}" for i in range(len(names)) for axis in ("X", "Y", "Z")),
    ]
    for frame in range(n_frames):
        row = [str(frame), f"{time_s[frame]:.6f}"]
        for name in names:
            x, y, z = markers[name][frame]
            row.extend([f"{x:.6f}", f"{y:.6f}", f"{z:.6f}"])
        lines.append("\t".join(row))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_mot(path: Path, columns: dict[str, list[float]], n_frames: int) -> None:
    time_s = np.arange(n_frames) * DT_S
    lines = [
        "Coordinates",
        "version=1",
        f"nRows={n_frames}",
        f"nColumns={len(columns) + 1}",
        "inDegrees=yes",
        "",
        "Units are S.I. units (second, meters, Newtons, ...)",
        "endheader",
        "time\t" + "\t".join(columns),
    ]
    for frame in range(n_frames):
        row = [f"{time_s[frame]:.6f}"] + [f"{columns[name][frame]:.6f}" for name in columns]
        lines.append("\t".join(row))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _markers(n_frames: int, x_start: float = -5.0, x_end: float = -3.0) -> dict[str, np.ndarray]:
    x = np.linspace(x_start, x_end, n_frames)
    markers: dict[str, np.ndarray] = {}
    for i, name in enumerate(MARKER_NAMES):
        markers[name] = np.column_stack(
            [x + 0.01 * i, np.full(n_frames, 0.9 + 0.01 * i), np.full(n_frames, 0.1 * i)]
        )
    return markers


@pytest.fixture
def trial(tmp_path: Path) -> tuple[Path, str]:
    _write_trc(tmp_path / "gehen.trc", _markers(N_FRAMES), N_FRAMES)
    _write_mot(tmp_path / "gehen.mot", MOT_COLUMNS, N_FRAMES)
    return tmp_path, "gehen"


def test_backend_name_and_camera_near_side(trial: tuple[Path, str]) -> None:
    trial_dir, name = trial
    result = load_opencap(trial_dir, name)
    assert result.backend == "opencap"
    assert result.keypoint_unit == "m"
    assert result.camera_near_side is None
    result.validate()


def test_sagittal_angles_are_passed_through_unclipped_samples(trial: tuple[Path, str]) -> None:
    trial_dir, name = trial
    result = load_opencap(trial_dir, name)
    knee_l = result.angles_deg["knee_flexion_deg_L"]
    np.testing.assert_allclose(knee_l, MOT_COLUMNS["knee_angle_l"])
    assert result.meta["clipped_frames"]["knee_flexion_deg_L"] == 0


def test_knee_clip_at_zero_degrees_becomes_nan(trial: tuple[Path, str]) -> None:
    trial_dir, name = trial
    result = load_opencap(trial_dir, name)
    knee_r = result.angles_deg["knee_flexion_deg_R"]
    assert np.isnan(knee_r[2])
    np.testing.assert_allclose(knee_r[[0, 1, 3, 4, 5]], [10.0, 20.0, 40.0, 50.0, 60.0])
    assert result.meta["clipped_frames"]["knee_flexion_deg_R"] == 1


def test_hip_flexion_clip_at_minus_30_becomes_nan(trial: tuple[Path, str]) -> None:
    trial_dir, name = trial
    result = load_opencap(trial_dir, name)
    hip_l = result.angles_deg["hip_flexion_deg_L"]
    assert np.isnan(hip_l[3])
    assert result.meta["clipped_frames"]["hip_flexion_deg_L"] == 1


def test_ankle_clip_at_minus_50_becomes_nan(trial: tuple[Path, str]) -> None:
    trial_dir, name = trial
    result = load_opencap(trial_dir, name)
    ankle_r = result.angles_deg["ankle_dorsiflexion_deg_R"]
    assert np.isnan(ankle_r[0])
    assert result.meta["clipped_frames"]["ankle_dorsiflexion_deg_R"] == 1


def test_frontal_and_transverse_channels_are_present(trial: tuple[Path, str]) -> None:
    trial_dir, name = trial
    result = load_opencap(trial_dir, name)
    np.testing.assert_allclose(result.angles_deg["pelvis_list_deg"], MOT_COLUMNS["pelvis_list"])
    np.testing.assert_allclose(
        result.angles_deg["hip_adduction_deg_R"], MOT_COLUMNS["hip_adduction_r"]
    )
    np.testing.assert_allclose(
        result.angles_deg["hip_adduction_deg_L"], MOT_COLUMNS["hip_adduction_l"]
    )
    np.testing.assert_allclose(
        result.angles_deg["hip_rotation_deg_R"], MOT_COLUMNS["hip_rotation_r"]
    )
    np.testing.assert_allclose(
        result.angles_deg["hip_rotation_deg_L"], MOT_COLUMNS["hip_rotation_l"]
    )


def test_new_canonical_channels_are_registered_in_the_schema() -> None:
    assert "pelvis_list_deg" in ANGLE_CHANNELS
    assert "hip_adduction_deg" in ANGLE_CHANNELS
    assert "hip_rotation_deg" in ANGLE_CHANNELS


def test_keypoints_are_read_in_metres(trial: tuple[Path, str]) -> None:
    trial_dir, name = trial
    result = load_opencap(trial_dir, name)
    assert "knee_L" in result.keypoints
    assert "heel_R" in result.keypoints
    assert result.keypoints["knee_L"].shape == (N_FRAMES, 3)


def test_walking_direction_from_mid_hip(trial: tuple[Path, str]) -> None:
    trial_dir, name = trial
    result = load_opencap(trial_dir, name)
    assert result.walking_direction == "+x"


def test_x_min_m_crops_to_a_contiguous_trailing_window(trial: tuple[Path, str]) -> None:
    trial_dir, name = trial
    # x runs linearly from -5.0 to -3.0 m over 6 frames (0.4 m/frame); -4.0 m is crossed
    # between frame 2 (-4.2) and frame 3 (-3.8).
    result = load_opencap(trial_dir, name, x_min_m=-4.0)
    assert result.n_frames == 3
    assert result.time_s[0] == pytest.approx(0.0)
    assert result.meta["frames_kept"] == "3:6 of 6"


def test_x_min_m_excluding_everything_raises(trial: tuple[Path, str]) -> None:
    trial_dir, name = trial
    with pytest.raises(ValueError, match="nothing left"):
        load_opencap(trial_dir, name, x_min_m=10.0)


def test_mismatched_frame_counts_raise(tmp_path: Path) -> None:
    _write_trc(tmp_path / "bad.trc", _markers(N_FRAMES), N_FRAMES)
    short_columns = {k: v[: N_FRAMES - 1] for k, v in MOT_COLUMNS.items()}
    _write_mot(tmp_path / "bad.mot", short_columns, N_FRAMES - 1)
    with pytest.raises(ValueError, match="frames"):
        load_opencap(tmp_path, "bad")

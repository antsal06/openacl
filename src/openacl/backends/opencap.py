"""OpenCap (2 iPhones, markerless 3-D) backend adapter (ADR-0011).

OpenCap (https://opencap.ai, LaiUhlrich2022 model, HRNet + LSTM augmenter) triangulates two
phones into a scaled OpenSim model and writes ``.mot`` (joint angles, degrees) and ``.trc``
(markers, metres) per trial -- the same text formats :mod:`openacl.backends._trc_mot` already
parses for Sports2D. This adapter is a reference/frontal-plane source (ADR-0002, ADR-0011), not
the production backend: it needs two calibrated phones and Stanford's processing service, and
the number of usable cycles per trial is small because the calibrated volume is short.

Sign conventions (verified 2026-09-10 against a real walking trial, see ADR-0011): OpenSim's
``knee_angle``, ``hip_flexion`` and ``ankle_angle`` coordinates are already flexion/dorsiflexion
positive, matching :mod:`openacl.schema`'s clinical convention -- no sign flip applied.
``pelvis_list`` (frontal-plane obliquity), ``hip_adduction`` and ``hip_rotation`` are passed
through as OpenSim reports them; their sign has not been separately verified against a clinical
convention (unlike the sagittal triad), so treat them as *raw OpenSim*, not as independently
checked clinical-sign channels -- ADR-0011 lists them as new canonical names precisely because
no other backend produces them yet.

IK saturation: a frame sitting exactly on one of OpenSim's coordinate limits (``knee_angle``
0.00 deg, ``hip_flexion`` -30.00 deg, ``ankle_angle`` -50.00 deg, checked per side) is inverse
kinematics hitting its joint limit, not a measurement, and is set to ``NaN`` in that channel
only; the count per channel is recorded in ``meta["clipped_frames"]``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from openacl.schema import KinematicsResult, sided

from ._trc_mot import read_mot, read_trc

BACKEND_NAME = "opencap"

# OpenSim LaiUhlrich2022 coordinate -> our canonical channel base name.
ANGLE_MAP: dict[str, str] = {
    "knee_angle": "knee_flexion_deg",
    "hip_flexion": "hip_flexion_deg",
    "ankle_angle": "ankle_dorsiflexion_deg",
}

# Frontal/transverse-plane channels only OpenCap provides (ADR-0011); no sagittal-only
# clip-limit check applies to these (see LIMITS_DEG below).
FRONTAL_ANGLE_MAP: dict[str, str] = {
    "hip_adduction": "hip_adduction_deg",
    "hip_rotation": "hip_rotation_deg",
}

# our keypoint base name -> OpenCap .trc marker prefix (schema.KEYPOINT_NAMES)
MARKER_MAP: dict[str, str] = {
    "hip": "Hip",
    "knee": "Knee",
    "ankle": "Ankle",
    "heel": "Heel",
    "big_toe": "BigToe",
    "small_toe": "SmallToe",
    "shoulder": "Shoulder",
}

# OpenSim coordinate limits (LaiUhlrich2022 model); a frame sitting exactly on one is IK
# saturation, not a measurement (ADR-0011).
LIMITS_DEG: dict[str, float] = {
    "knee_angle": 0.0,
    "hip_flexion": -30.0,
    "ankle_angle": -50.0,
}
CLIP_ATOL_DEG = 0.05


def _clip_to_nan(
    raw: np.ndarray, limit_deg: float, atol_deg: float = CLIP_ATOL_DEG
) -> tuple[np.ndarray, int]:
    """Return ``(values_with_nan_at_the_limit, n_clipped)``."""
    mask = np.isclose(raw, limit_deg, atol=atol_deg)
    values = raw.copy()
    values[mask] = np.nan
    return values, int(mask.sum())


def load_opencap(
    trial_dir: Path | str, trial: str, x_min_m: float | None = None
) -> KinematicsResult:
    """Load one OpenCap trial (``<trial_dir>/<trial>.mot`` + ``.trc``) as a ``KinematicsResult``.

    Parameters
    ----------
    trial_dir
        Directory containing the trial's ``.mot`` and ``.trc`` export.
    trial
        Trial name, without extension.
    x_min_m
        Optional lower bound (in the calibration frame's x axis, metres) for the mid-hip
        position; frames before the subject reaches this x are dropped. The default, ``None``,
        keeps every frame -- callers who know where IK saturation starts for their own
        calibration (see ``meta["clipped_frames"]``) can crop it out this way. The kept window
        is always contiguous (gait-core needs a continuous time base): once ``x_min_m`` is first
        reached, every following frame is kept even if a single sample later dips back below it.

    Raises
    ------
    ValueError
        If the ``.mot`` and ``.trc`` frame counts disagree, or nothing is left after
        ``x_min_m`` is applied.
    """
    trial_dir = Path(trial_dir)
    mot = read_mot(trial_dir / f"{trial}.mot")
    trc = read_trc(trial_dir / f"{trial}.trc")
    if len(mot.time_s) != len(trc.time_s):
        raise ValueError(f"{trial}: .mot has {len(mot.time_s)} frames, .trc has {len(trc.time_s)}")

    keep = np.ones(len(mot.time_s), dtype=bool)
    if x_min_m is not None:
        keep &= trc.markers["midHip"][:, 0] >= x_min_m
    idx = np.flatnonzero(keep)
    if idx.size == 0:
        raise ValueError(f"{trial}: nothing left after the x >= {x_min_m} m cut")
    lo, hi = int(idx[0]), int(idx[-1]) + 1  # contiguous window

    time_s = mot.time_s[lo:hi] - mot.time_s[lo]

    angles: dict[str, np.ndarray] = {}
    clipped_frames: dict[str, int] = {}
    for osim_base, ours in ANGLE_MAP.items():
        limit = LIMITS_DEG.get(osim_base)
        for osim_side, ours_side in (("r", "R"), ("l", "L")):
            raw = mot.angles[f"{osim_base}_{osim_side}"][lo:hi]
            key = sided(ours, ours_side)
            if limit is not None:
                values, n_clipped = _clip_to_nan(raw, limit)
                angles[key] = values
                clipped_frames[key] = n_clipped
            else:  # pragma: no cover - every entry in ANGLE_MAP currently has a limit
                angles[key] = raw

    for osim_base, ours in FRONTAL_ANGLE_MAP.items():
        for osim_side, ours_side in (("r", "R"), ("l", "L")):
            angles[sided(ours, ours_side)] = mot.angles[f"{osim_base}_{osim_side}"][lo:hi]

    angles["pelvis_tilt_deg"] = mot.angles["pelvis_tilt"][lo:hi]
    angles["pelvis_list_deg"] = mot.angles["pelvis_list"][lo:hi]

    keypoints: dict[str, np.ndarray] = {}
    for ours, oc in MARKER_MAP.items():
        for side in ("L", "R"):
            name = f"{side}{oc}"
            if name in trc.markers:
                keypoints[sided(ours, side)] = trc.markers[name][lo:hi]

    x = trc.markers["midHip"][lo:hi, 0]
    direction = "+x" if x[-1] > x[0] else "-x"

    return KinematicsResult(
        backend=BACKEND_NAME,
        fps=float(round(1.0 / np.median(np.diff(mot.time_s)))),
        time_s=time_s,
        angles_deg=angles,
        keypoints=keypoints,
        keypoint_unit="m",
        walking_direction=direction,
        camera_near_side=None,  # 3-D: neither side is camera-privileged
        meta={
            "trial": trial,
            "frames_kept": f"{lo}:{hi} of {len(mot.time_s)}",
            "x_min_m": x_min_m,
            "clipped_frames": clipped_frames,
            "clip_limits_deg": LIMITS_DEG,
        },
    )

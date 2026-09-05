"""Sports2D backend adapter: 1 sagittal smartphone video -> :class:`KinematicsResult`.

Sports2D (https://github.com/davidpagnon/Sports2D) wraps RTMLib pose estimation (HALPE_26,
``body_with_feet`` model) plus 2-D joint/segment angle computation. This module calls it
programmatically (a config ``dict``, not a TOML file), then reads the ``.trc`` (pose, pixels
or metres) and ``.mot`` (angles, degrees) files it writes -- see :mod:`openacl.backends._trc_mot`
for the parsers, no pickle involved.

Sign conventions (verified empirically against the bundled Sports2D demo video, see the report
for this work package): Sports2D's own ``angle_dict`` (``Pose2Sim/common.py``) already encodes
clinical sign for the joint angles this adapter uses -- knee flexion, hip flexion and ankle
dorsiflexion are all positive in Sports2D's raw ``.mot`` output, matching ADR-0007 exactly. No
extra sign flip is applied to those three. ``trunk_lean_deg`` needs one conversion (segment
angle vs. horizontal -> lean vs. vertical, see :func:`_trunk_lean_from_segment_deg`).
``pelvis_tilt_deg`` is deliberately left absent: pelvic tilt is a frontal/transverse-plane
rotation and a single sagittal camera geometrically cannot observe it, so Sports2D's 2-D
"pelvis" segment angle (LHip-RHip vector) is close to pure noise. Fill it only via
``extra_config`` if you understand that limitation.

Left/right: Sports2D's ``body_with_feet`` (HALPE_26) keypoints are already the *subject's*
anatomical left/right (``LKnee``, ``RKnee``, ...), not image left/right -- see
``Pose2Sim.skeletons.HALPE_26``. ``visible_side`` only controls an internal X-flip Sports2D
applies before computing angle *sign* (so angles come out correct regardless of which way the
subject walks on screen) and does not relabel keypoints. This adapter reads the un-flipped pose
(pixel/metre) coordinates straight from the ``.trc`` file.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Literal

import numpy as np

from openacl.schema import KinematicsResult, Side, sided

from ._trc_mot import read_mot, read_trc
from .video import VideoInfo, probe

logger = logging.getLogger(__name__)

Mode = Literal["lightweight", "balanced", "performance"]
VisibleSide = Literal["auto", "left", "right", "front", "back", "none"]

# HALPE_26 marker name (Pose2Sim.skeletons.HALPE_26 / Sports2D CUSTOM tracking tree) ->
# (schema keypoint base name, side). These are already the subject's anatomical sides.
_KEYPOINT_MAP: dict[str, tuple[str, Side]] = {
    "RHip": ("hip", "R"),
    "LHip": ("hip", "L"),
    "RKnee": ("knee", "R"),
    "LKnee": ("knee", "L"),
    "RAnkle": ("ankle", "R"),
    "LAnkle": ("ankle", "L"),
    "RHeel": ("heel", "R"),
    "LHeel": ("heel", "L"),
    "RBigToe": ("big_toe", "R"),
    "LBigToe": ("big_toe", "L"),
    "RSmallToe": ("small_toe", "R"),
    "LSmallToe": ("small_toe", "L"),
    "RShoulder": ("shoulder", "R"),
    "LShoulder": ("shoulder", "L"),
}

# Sports2D .mot joint-angle columns (always lowercase, see Sports2D.process.process_fun) that
# map 1:1 onto schema angle channels with clinical sign already correct. See module docstring
# and Pose2Sim/common.py:angle_dict for the offset/scale that makes this true:
#   'right knee': [['RAnkle','RKnee','RHip'], 'flexion', -180, 1]
#   'right hip':  [['RKnee','RHip','Hip','Neck'], 'flexion', 0, -1]
#   'right ankle':[['RKnee','RAnkle','RBigToe','RHeel'], 'dorsiflexion', 90, 1]
_JOINT_ANGLE_MAP: dict[str, tuple[str, Side]] = {
    "right knee": ("knee_flexion_deg", "R"),
    "left knee": ("knee_flexion_deg", "L"),
    "right hip": ("hip_flexion_deg", "R"),
    "left hip": ("hip_flexion_deg", "L"),
    "right ankle": ("ankle_dorsiflexion_deg", "R"),
    "left ankle": ("ankle_dorsiflexion_deg", "L"),
}

_TRUNK_COLUMN = "trunk"
_PELVIS_COLUMN = "pelvis"

DEFAULT_DET_FREQUENCY = 4
"""Run person detection every N frames; keypoint detection still runs every frame. Raise this
(e.g. to 8-10) if RAM is tight on an 8 GB machine -- detection, not pose estimation, is the
peak-RAM step for the 'performance' mode's yolox_x detector."""


def _deep_merge(base: dict, overrides: dict) -> dict:
    """Recursively merge ``overrides`` into a copy of ``base``; used for ``extra_config``."""
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _sports2d_version() -> str:
    try:
        return version("sports2d")
    except PackageNotFoundError:
        return "unknown"


def _build_config(
    video: Path,
    out_dir: Path,
    *,
    mode: Mode,
    to_meters: bool,
    person_height_m: float | None,
    visible_side: VisibleSide,
    det_frequency: int,
) -> dict:
    """Build the Sports2D config dict for one single-person, headless run.

    ``person_ordering_method='highest_likelihood'`` is used instead of Sports2D's own default
    (``'on_click'``) because ``'on_click'`` opens a blocking matplotlib window even when
    ``nb_persons_to_detect=1`` -- unusable in a script/CLI context.

    ``post-processing.interpolate=True`` with ``interp_gap_smaller_than=0`` and
    ``fill_large_gaps_with='nan'`` together disable Sports2D's own gap-filling: internally,
    undetected frames are a ``0.0`` sentinel that only ``interpolate=True`` converts to real
    ``NaN`` (see ``Pose2Sim.common.interpolate_zeros_nans``); setting the gap-length threshold
    to 0 means every real gap is treated as "too long to interpolate" and reintroduced as NaN,
    and ``fill_large_gaps_with='nan'`` (not Sports2D's default ``'last_value'``) stops the
    following forward/backward-fill step from fabricating values across those gaps. This keeps
    the ADR-0007 contract ("NaN for missing values, no interpolation happens inside a backend")
    as close as this backend allows.
    """
    return {
        "base": {
            "video_input": [str(video)],
            "video_dir": "",
            "result_dir": str(out_dir),
            "person_ordering_method": "highest_likelihood",
            "nb_persons_to_detect": 1,
            "visible_side": [visible_side],
            "first_person_height": person_height_m if person_height_m is not None else 1.70,
            "show_realtime_results": False,
            "save_vid": False,
            "save_img": False,
            "save_pose": True,
            "calculate_angles": True,
            "save_angles": True,
        },
        "pose": {
            "pose_model": "body_with_feet",
            "mode": mode,
            "det_frequency": det_frequency,
            "device": "auto",
            "backend": "auto",
        },
        "px_to_meters_conversion": {
            "to_meters": to_meters,
        },
        "post-processing": {
            "show_graphs": False,
            "save_graphs": False,
            "interpolate": True,
            "interp_gap_smaller_than": 0,
            "fill_large_gaps_with": "nan",
            "reject_outliers": True,
        },
    }


def _resolve_output_files(out_dir: Path, video: Path, to_meters: bool) -> tuple[Path, Path]:
    run_dir = out_dir / f"{video.stem}_Sports2D"
    suffix = "m" if to_meters else "px"
    trc_path = run_dir / f"{video.stem}_Sports2D_{suffix}_person00.trc"
    mot_path = run_dir / f"{video.stem}_Sports2D_angles_person00.mot"
    if not trc_path.exists():
        raise FileNotFoundError(
            f"Sports2D did not produce the expected pose file: {trc_path}. "
            f"Check {run_dir / 'logs.txt'} for details (e.g. no person detected)."
        )
    if not mot_path.exists():
        raise FileNotFoundError(
            f"Sports2D did not produce the expected angles file: {mot_path}. "
            f"Check {run_dir / 'logs.txt'} for details."
        )
    return trc_path, mot_path


def _trunk_lean_from_segment_deg(trunk_segment_deg: np.ndarray) -> np.ndarray:
    """Convert Sports2D's 'trunk' segment angle (vs. horizontal) to forward lean (vs. vertical).

    Sports2D: ``'trunk': [['Neck', 'Hip'], 'horizontal', 0, -1]``, a 2-point segment angle
    between the horizontal and the Neck->Hip vector. An upright trunk is vertical, i.e. reads
    ~90 deg in that convention; empirically (bundled demo video) the value stays close to 90
    deg with a few degrees of spread. ``90 - trunk_deg`` maps upright to 0 and, because
    Sports2D's internal X-flip normalises gait progression to the flipped-frame +x direction
    before computing any angle, forward lean (in the direction of walking) comes out positive
    -- consistent with the flexion-positive spirit of the other channels. This is an
    interpretation choice (see report), not something Sports2D documents directly.
    """
    return 90.0 - trunk_segment_deg


def _resolve_camera_near_side(
    markers: dict[str, np.ndarray], visible_side: VisibleSide
) -> Side | None:
    """Determine the camera-facing side, replicating Sports2D's own 'auto' heuristic when asked.

    Sports2D (``Sports2D.process.compute_angles_for_person``, ``visible_side_str == 'auto'``)
    decides the visible side per frame from foot orientation::

        right_orientation = RBigToe_x - RHeel_x
        left_orientation  = LBigToe_x - LHeel_x
        side = 'right' if (right_orientation + left_orientation) >= 0 else 'left'

    Sports2D does not persist this resolved side to any output file, so this adapter
    recomputes it from the toe/heel columns already available in the parsed pose, majority-
    voted over valid frames, for consistency with what Sports2D used internally for its own
    angle-sign flip.
    """
    if visible_side in ("left", "right"):
        return "L" if visible_side == "left" else "R"
    if visible_side in ("front", "back", "none"):
        return None

    required = ("RBigToe", "RHeel", "LBigToe", "LHeel")
    if not all(name in markers for name in required):
        return None
    r_toe, r_heel = markers["RBigToe"][:, 0], markers["RHeel"][:, 0]
    l_toe, l_heel = markers["LBigToe"][:, 0], markers["LHeel"][:, 0]
    orientation = (r_toe - r_heel) + (l_toe - l_heel)
    valid = ~np.isnan(orientation)
    if not np.any(valid):
        return None
    return "R" if np.nanmean(orientation[valid]) >= 0 else "L"


def _walking_direction(markers: dict[str, np.ndarray]) -> Literal["+x", "-x", "unknown"]:
    """Direction of progression from the hip-x time course (mean of L/R hip, or whichever
    is present), per the CLI/backend spec: independent of Sports2D's internal X-flip, which
    only affects the *angles* it computes, not the raw pose coordinates this reads.
    """
    xs = [markers[name][:, 0] for name in ("RHip", "LHip") if name in markers]
    if not xs:
        return "unknown"
    hip_x = np.nanmean(np.column_stack(xs), axis=1) if len(xs) > 1 else xs[0]
    valid = np.flatnonzero(~np.isnan(hip_x))
    if valid.size < 2:
        return "unknown"
    delta = hip_x[valid[-1]] - hip_x[valid[0]]
    if delta > 0:
        return "+x"
    if delta < 0:
        return "-x"
    return "unknown"


@dataclass(frozen=True)
class _ParsedRun:
    time_s: np.ndarray
    fps: float
    markers: dict[str, np.ndarray]
    keypoint_unit: Literal["px", "m"]
    angles_raw: dict[str, np.ndarray]


def run_sports2d(
    video: Path | str,
    out_dir: Path | str,
    *,
    mode: Mode = "balanced",
    to_meters: bool = False,
    person_height_m: float | None = None,
    visible_side: VisibleSide = "auto",
    extra_config: dict | None = None,
) -> KinematicsResult:
    """Run Sports2D on ``video`` and return the result as a :class:`KinematicsResult`.

    Parameters
    ----------
    video
        Path to a sagittal, single-person gait video.
    out_dir
        Directory to write Sports2D's own output into (a ``<video_stem>_Sports2D`` folder is
        created inside it) and where ``result.save(out_dir / "kinematics")`` is called.
    mode
        ``"lightweight"``, ``"balanced"`` or ``"performance"`` (see ``rtmlib``'s
        ``BodyWithFeet.MODE``): trades detector/pose-model size for speed. On an 8 GB, CPU-only
        Apple M2, ``"lightweight"`` and ``"balanced"`` are both practical (see report for
        measured throughput); ``"performance"`` is markedly slower and RAM-heavier.
    to_meters
        Convert pixel coordinates to metres using ``person_height_m`` (Sports2D's own
        perspective correction). Keeps ``keypoint_unit="px"`` (2-D) when ``False``, switches to
        ``"m"`` (3-D, with a synthetic ``Z``) when ``True``.
    person_height_m
        Subject height in metres, used only when ``to_meters=True``.
    visible_side
        ``"auto"`` (per-frame foot-orientation heuristic, Sports2D's own default logic),
        or an explicit side/orientation.
    extra_config
        Deep-merged on top of this adapter's own Sports2D config dict; use it to override
        anything (e.g. ``{"pose": {"det_frequency": 8}}`` to cut RAM/CPU further).

    Raises
    ------
    ImportError
        If the optional ``sports2d`` dependency is not installed
        (``uv pip install --python .venv/bin/python sports2d``).
    """
    try:
        from Sports2D import Sports2D as _sports2d_module
    except ImportError as exc:  # pragma: no cover - exercised only without the optional dep
        raise ImportError(
            "The 'sports2d' backend needs the optional 'sports2d' package: "
            "uv pip install --python .venv/bin/python sports2d"
        ) from exc

    video = Path(video)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    video_info: VideoInfo = probe(video)
    for warning in video_info.warnings:
        logger.warning("%s: %s", video, warning)

    config = _build_config(
        video,
        out_dir,
        mode=mode,
        to_meters=to_meters,
        person_height_m=person_height_m,
        visible_side=visible_side,
        det_frequency=DEFAULT_DET_FREQUENCY,
    )
    if extra_config:
        config = _deep_merge(config, extra_config)

    t0 = time.time()
    _sports2d_module.process(config)
    runtime_s = time.time() - t0

    trc_path, mot_path = _resolve_output_files(out_dir, video, to_meters)
    trc = read_trc(trc_path)
    mot = read_mot(mot_path)

    if trc.time_s.shape[0] != mot.time_s.shape[0]:
        raise ValueError(
            f"pose and angle files disagree on frame count: {trc.time_s.shape[0]} vs "
            f"{mot.time_s.shape[0]} ({trc_path.name} vs {mot_path.name})"
        )

    n_frames = trc.time_s.shape[0]

    keypoints: dict[str, np.ndarray] = {}
    confidence: dict[str, np.ndarray] = {}
    for marker_name, (base_name, side) in _KEYPOINT_MAP.items():
        if marker_name not in trc.markers:
            continue
        xyz = trc.markers[marker_name]
        coords = xyz if to_meters else xyz[:, :2]
        key = sided(base_name, side)
        keypoints[key] = coords
        # Sports2D does not persist per-keypoint confidence to the .trc file (only used
        # in-memory during person selection/floor estimation), so we fall back to a NaN mask:
        # 1.0 where the coordinate is present, 0.0 where it is NaN. Recorded in meta below.
        present = ~np.isnan(coords).any(axis=1)
        confidence[key] = present.astype(float)

    angles_deg: dict[str, np.ndarray] = {}
    for mot_name, (base_name, side) in _JOINT_ANGLE_MAP.items():
        if mot_name in mot.angles:
            angles_deg[sided(base_name, side)] = mot.angles[mot_name]
    if _TRUNK_COLUMN in mot.angles:
        angles_deg["trunk_lean_deg"] = _trunk_lean_from_segment_deg(mot.angles[_TRUNK_COLUMN])
    # pelvis_tilt_deg deliberately omitted -- see module docstring.

    camera_near_side = _resolve_camera_near_side(trc.markers, visible_side)
    direction = _walking_direction(trc.markers)

    result = KinematicsResult(
        backend="sports2d",
        fps=trc.fps,
        time_s=trc.time_s,
        angles_deg=angles_deg,
        keypoints=keypoints,
        keypoint_unit="m" if to_meters else "px",
        confidence=confidence,
        walking_direction=direction,
        camera_near_side=camera_near_side,
        meta={
            "video": str(video),
            "video_fps": video_info.fps,
            "video_width": video_info.width,
            "video_height": video_info.height,
            "video_n_frames": video_info.n_frames,
            "video_codec": video_info.codec,
            "video_warnings": list(video_info.warnings),
            "sports2d_version": _sports2d_version(),
            "pose_model": "body_with_feet (HALPE_26)",
            "mode": mode,
            "visible_side_config": visible_side,
            "config": config,
            "runtime_s": runtime_s,
            "n_frames": n_frames,
            "confidence_source": "nan_mask",
            "confidence_note": (
                "Sports2D does not output per-keypoint confidence to file; confidence is 1.0 "
                "where the parsed coordinate is not NaN and 0.0 where it is NaN."
            ),
            "pelvis_tilt_omitted": (
                "pelvis_tilt_deg is not observable from a single sagittal camera "
                "(frontal/transverse-plane rotation); Sports2D's 2-D 'pelvis' segment angle is "
                "not exposed here for that reason -- see backends/sports2d.py docstring."
            ),
        },
    )
    result.validate()
    result.save(out_dir / "kinematics")
    return result

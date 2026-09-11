"""Shared output schema of the kinematics engine (layer 2), consumed by gait-core (layer 3).

Every backend (sports2d, pose2sim, opencap_mono in research/) must produce a
``KinematicsResult``. Gait-core never imports a backend; it only consumes this type.

Conventions
-----------
- Time series are 1-D ``numpy`` arrays of length ``n_frames`` sampled at ``fps``.
  Missing values are ``NaN``. No interpolation happens inside a backend.
- Angles are in degrees and follow clinical sign conventions:
  knee flexion positive, hip flexion positive, ankle dorsiflexion positive.
- Side suffix is always ``_L`` / ``_R`` (subject's left/right, not image side).
- Keypoints are stored per name with shape ``(n_frames, 2)`` in pixels for 2-D backends
  and ``(n_frames, 3)`` in metres for 3-D backends. ``keypoint_unit`` says which.
- Every number carries its unit in the name (``_deg``, ``_s``, ``_px``, ``_m``) or in the type.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np

Side = Literal["L", "R"]

# Canonical angle names. Backends map their own names onto these.
# Not every backend fills every channel; absent channels are simply missing keys.
ANGLE_CHANNELS: tuple[str, ...] = (
    "hip_flexion_deg",
    "knee_flexion_deg",
    "ankle_dorsiflexion_deg",
    "trunk_lean_deg",  # segment angle vs vertical, no side
    "pelvis_tilt_deg",  # sagittal, no side
    "pelvis_list_deg",  # frontal-plane pelvis obliquity, no side (ADR-0011, opencap only)
    "hip_adduction_deg",  # frontal plane (ADR-0011, opencap only)
    "hip_rotation_deg",  # transverse plane (ADR-0011, opencap only)
)

# Canonical keypoint names (subset of COCO/Halpe-26 that gait-core relies on).
KEYPOINT_NAMES: tuple[str, ...] = (
    "hip",
    "knee",
    "ankle",
    "heel",
    "big_toe",
    "small_toe",
    "shoulder",
)


def sided(name: str, side: Side) -> str:
    """Return ``name`` with side suffix, e.g. ``sided("knee_flexion_deg", "L")``."""
    return f"{name}_{side}"


@dataclass
class KinematicsResult:
    """Backend-independent kinematics of one walking pass (one video, one person)."""

    backend: str
    """Backend identifier, e.g. ``"sports2d"``, ``"pose2sim"``, ``"opencap_mono"``."""

    fps: float
    time_s: np.ndarray
    """Shape ``(n_frames,)``; monotonically increasing, starts at 0."""

    angles_deg: dict[str, np.ndarray] = field(default_factory=dict)
    """Keys like ``"knee_flexion_deg_L"``; values shape ``(n_frames,)`` with NaN gaps."""

    keypoints: dict[str, np.ndarray] = field(default_factory=dict)
    """Keys like ``"heel_L"``; values shape ``(n_frames, 2)`` or ``(n_frames, 3)``."""

    keypoint_unit: Literal["px", "m"] = "px"

    confidence: dict[str, np.ndarray] = field(default_factory=dict)
    """Per-keypoint detection confidence in [0, 1], same keys as ``keypoints``."""

    walking_direction: Literal["+x", "-x", "unknown"] = "unknown"
    """Direction of progression in the keypoint frame; needed to decide camera-near side."""

    camera_near_side: Side | None = None
    """Side facing the camera in a sagittal video; more reliable than the far side."""

    meta: dict = field(default_factory=dict)
    """Free-form provenance: source video, model, backend version, config hash, ..."""

    # ------------------------------------------------------------------ helpers
    @property
    def n_frames(self) -> int:
        return int(self.time_s.shape[0])

    def angle(self, name: str, side: Side | None = None) -> np.ndarray:
        """Return one angle channel; raises ``KeyError`` if the backend did not produce it."""
        return self.angles_deg[sided(name, side) if side else name]

    def validate(self) -> None:
        """Raise ``ValueError`` on shape or unit inconsistencies."""
        n = self.n_frames
        if self.fps <= 0:
            raise ValueError("fps must be positive")
        if np.any(np.diff(self.time_s) <= 0):
            raise ValueError("time_s must be strictly increasing")
        for k, v in self.angles_deg.items():
            if v.shape != (n,):
                raise ValueError(f"angle {k!r} has shape {v.shape}, expected ({n},)")
        dim = 2 if self.keypoint_unit == "px" else 3
        for k, v in self.keypoints.items():
            if v.shape != (n, dim):
                raise ValueError(f"keypoint {k!r} has shape {v.shape}, expected ({n}, {dim})")
            if k in self.confidence and self.confidence[k].shape != (n,):
                raise ValueError(f"confidence {k!r} has wrong shape")

    # ------------------------------------------------------------- persistence
    def save(self, path: Path | str) -> None:
        """Write to ``<path>.npz`` (arrays) plus ``<path>.json`` (scalars and meta)."""
        path = Path(path)
        arrays = {"time_s": self.time_s}
        arrays.update({f"angle::{k}": v for k, v in self.angles_deg.items()})
        arrays.update({f"kp::{k}": v for k, v in self.keypoints.items()})
        arrays.update({f"conf::{k}": v for k, v in self.confidence.items()})
        np.savez_compressed(path.with_suffix(".npz"), **arrays)
        scalars = {
            "backend": self.backend,
            "fps": self.fps,
            "keypoint_unit": self.keypoint_unit,
            "walking_direction": self.walking_direction,
            "camera_near_side": self.camera_near_side,
            "meta": self.meta,
        }
        path.with_suffix(".json").write_text(json.dumps(scalars, indent=2, default=str))

    @classmethod
    def load(cls, path: Path | str) -> KinematicsResult:
        path = Path(path)
        arrays = np.load(path.with_suffix(".npz"))
        scalars = json.loads(path.with_suffix(".json").read_text())
        res = cls(
            backend=scalars["backend"],
            fps=float(scalars["fps"]),
            time_s=arrays["time_s"],
            keypoint_unit=scalars["keypoint_unit"],
            walking_direction=scalars["walking_direction"],
            camera_near_side=scalars["camera_near_side"],
            meta=scalars["meta"],
        )
        for k in arrays.files:
            if k.startswith("angle::"):
                res.angles_deg[k[7:]] = arrays[k]
            elif k.startswith("kp::"):
                res.keypoints[k[4:]] = arrays[k]
            elif k.startswith("conf::"):
                res.confidence[k[6:]] = arrays[k]
        return res

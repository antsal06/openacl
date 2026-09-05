"""Synthetic gait generator producing a ``KinematicsResult`` with known ground truth.

Model (sagittal plane, ``x`` = direction of progression, ``y`` = vertical, up positive):

- The pelvis advances at constant speed; ``hip_L``/``hip_R`` oscillate in anti-phase so that
  their mean (the Zeni reference) is exactly linear in ``x``.
- Each foot is planted at a fixed ``x`` from heel strike to toe off and then swings forward by
  one stride length. The swing profile is a cubic Hermite with prescribed end slopes, so the
  heel is still travelling forward at contact. That makes ``max(heel_x - hip_x)`` fall exactly
  on the heel strike frame and ``min(toe_x - hip_x)`` on the toe-off frame, which is what
  Zeni et al. 2008 assumes.
- Knee and hip angles are periodic wrapped-Gaussian / cosine shapes with known peak values
  (default: 15 deg loading-response peak and 60 deg swing peak, cf. Perry & Burnfield).

The heel and the toe get slightly different swing profiles, i.e. the foot is not modelled as a
rigid body. This is a test signal, not a biomechanical simulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from openacl.schema import KinematicsResult, Side, sided

SIDES: tuple[Side, Side] = ("L", "R")
KNEE_LOADING_MU = 0.15
KNEE_LOADING_SIGMA = 0.07
KNEE_SWING_MU = 0.73
KNEE_SWING_SIGMA = 0.10
HEEL_AHEAD_AT_CONTACT_M = 0.35
"""Forward distance of the heel relative to the mid-hip at initial contact."""


@dataclass
class SyntheticGaitConfig:
    """Knobs of the synthetic walker. Times in seconds, lengths in metres, angles in degrees."""

    fps: float = 60.0
    n_cycles: int = 14
    stride_time_s: float = 1.1
    stance_pct_L: float = 60.0
    stance_pct_R: float | None = None
    """``None`` means the same as the left side (symmetric gait)."""
    right_offset_pct: float = 50.0
    """Phase of the right heel strike within the left stride."""
    speed_m_s: float = 1.3
    foot_length_m: float = 0.20
    hip_height_m: float = 0.95
    hip_sway_m: float = 0.01
    swing_height_m: float = 0.12
    base_knee_deg: float = 3.0
    peak_knee_stance_deg_L: float = 15.0
    peak_knee_swing_deg_L: float = 60.0
    peak_knee_stance_deg_R: float | None = None
    peak_knee_swing_deg_R: float | None = None
    hip_mean_deg: float = 10.0
    hip_amplitude_deg: float = 20.0
    unit: str = "px"
    """``"px"`` gives 2-D keypoints in pixels, ``"m"`` gives 3-D keypoints in metres."""
    pixels_per_m: float = 400.0
    direction: str = "+x"
    declare_direction: bool = True
    """``False`` sets ``walking_direction="unknown"`` so the estimator has to work it out."""
    noise_deg: float = 0.0
    noise_px: float = 0.0
    nan_gaps_s: tuple[tuple[float, float], ...] = ()
    nan_channels: tuple[str, ...] = ()
    """Channel/keypoint keys to blank inside ``nan_gaps_s``; empty means all of them."""
    confidence: float = 0.95
    confidence_far_side: float | None = None
    camera_near_side: Side | None = "R"
    heel_initial_slope: float = 0.0
    heel_terminal_slope: float = 0.8
    toe_initial_slope: float = 0.8
    toe_terminal_slope: float = 0.8
    seed: int = 0

    # ------------------------------------------------------------------ derived
    def stance_pct(self, side: Side) -> float:
        if side == "L" or self.stance_pct_R is None:
            return self.stance_pct_L
        return self.stance_pct_R

    def peak_knee_stance_deg(self, side: Side) -> float:
        if side == "L" or self.peak_knee_stance_deg_R is None:
            return self.peak_knee_stance_deg_L
        return self.peak_knee_stance_deg_R

    def peak_knee_swing_deg(self, side: Side) -> float:
        if side == "L" or self.peak_knee_swing_deg_R is None:
            return self.peak_knee_swing_deg_L
        return self.peak_knee_swing_deg_R

    @property
    def stride_length_m(self) -> float:
        return self.speed_m_s * self.stride_time_s

    @property
    def duration_s(self) -> float:
        return (self.n_cycles + 1) * self.stride_time_s

    def first_hs_s(self, side: Side) -> float:
        lead = 0.5 * self.stride_time_s
        if side == "L":
            return lead
        return lead + self.right_offset_pct / 100.0 * self.stride_time_s


@dataclass
class SyntheticTruth:
    """Ground truth of one generated walking pass."""

    fps: float
    stride_time_s: float
    heel_strikes: dict[Side, np.ndarray]
    toe_offs: dict[Side, np.ndarray]
    heel_strike_times_s: dict[Side, np.ndarray]
    toe_off_times_s: dict[Side, np.ndarray]
    stance_pct: dict[Side, float]
    swing_pct: dict[Side, float]
    stance_time_s: dict[Side, float]
    swing_time_s: dict[Side, float]
    step_time_s: dict[Side, float]
    step_length_m: dict[Side, float]
    double_support_pct: float
    cadence_steps_per_min: float
    stride_length_m: float
    walking_speed_m_s: float
    peak_knee_stance_deg: dict[Side, float]
    peak_knee_swing_deg: dict[Side, float]
    knee_curve_deg: dict[Side, np.ndarray] = field(default_factory=dict)
    """Noise-free knee curve on the 101-point phase grid, per side."""


def _hermite_swing(u: np.ndarray, initial_slope: float, terminal_slope: float) -> np.ndarray:
    """Cubic Hermite from 0 to 1 with prescribed end slopes (normalised swing displacement)."""
    u = np.clip(u, 0.0, 1.0)
    return (
        (-2 * u**3 + 3 * u**2)
        + initial_slope * (u**3 - 2 * u**2 + u)
        + terminal_slope * (u**3 - u**2)
    )


def _wrapped_gaussian(phase: np.ndarray, mu: float, sigma: float) -> np.ndarray:
    """Periodic Gaussian bump on the unit cycle, peak value 1 at ``mu``."""
    total = np.zeros_like(phase)
    for shift in (-1.0, 0.0, 1.0):
        total += np.exp(-0.5 * ((phase - mu + shift) / sigma) ** 2)
    return total


def knee_curve_deg(
    phase: np.ndarray, base_deg: float, peak_stance_deg: float, peak_swing_deg: float
) -> np.ndarray:
    """Knee flexion over the normalised cycle: loading-response bump plus swing bump."""
    return (
        base_deg
        + (peak_stance_deg - base_deg)
        * _wrapped_gaussian(phase, KNEE_LOADING_MU, KNEE_LOADING_SIGMA)
        + (peak_swing_deg - base_deg) * _wrapped_gaussian(phase, KNEE_SWING_MU, KNEE_SWING_SIGMA)
    )


def hip_curve_deg(phase: np.ndarray, mean_deg: float, amplitude_deg: float) -> np.ndarray:
    """Hip flexion: ~30 deg at initial contact, ~-10 deg in terminal stance."""
    return mean_deg + amplitude_deg * np.cos(2 * np.pi * phase)


def _foot_x_m(
    time_s: np.ndarray,
    first_hs_s: float,
    stride_time_s: float,
    stance_time_s: float,
    stride_length_m: float,
    x0_m: float,
    initial_slope: float,
    terminal_slope: float,
) -> np.ndarray:
    """Absolute forward position of a foot landmark: planted in stance, Hermite swing."""
    k = np.arange(-3, int(np.ceil(time_s[-1] / stride_time_s)) + 4)
    hs = first_hs_s + k * stride_time_s
    planted = x0_m + k * stride_length_m
    idx = np.clip(np.searchsorted(hs, time_s, side="right") - 1, 0, hs.size - 1)
    tau = time_s - hs[idx]
    swing_time_s = stride_time_s - stance_time_s
    u = (tau - stance_time_s) / swing_time_s
    return planted[idx] + stride_length_m * _hermite_swing(u, initial_slope, terminal_slope)


def make_synthetic_gait(
    config: SyntheticGaitConfig | None = None, **overrides
) -> tuple[KinematicsResult, SyntheticTruth]:
    """Generate a ``KinematicsResult`` plus its ground truth."""
    cfg = config or SyntheticGaitConfig()
    for key, value in overrides.items():
        if not hasattr(cfg, key):
            raise TypeError(f"unknown SyntheticGaitConfig field {key!r}")
        setattr(cfg, key, value)

    rng = np.random.default_rng(cfg.seed)
    fps, stride_time_s = float(cfg.fps), float(cfg.stride_time_s)
    n_frames = round(cfg.duration_s * fps) + 1
    time_s = np.arange(n_frames, dtype=float) / fps
    direction_sign = 1.0 if cfg.direction == "+x" else -1.0
    scale = cfg.pixels_per_m if cfg.unit == "px" else 1.0
    phase_grid = np.linspace(0.0, 1.0, 101)

    angles: dict[str, np.ndarray] = {}
    keypoints_m: dict[str, np.ndarray] = {}
    truth: dict[str, dict[Side, object]] = {
        "hs_frames": {},
        "to_frames": {},
        "hs_times": {},
        "to_times": {},
        "stance_pct": {},
        "stance_time_s": {},
        "swing_time_s": {},
        "peak_stance": {},
        "peak_swing": {},
        "knee_curve": {},
        "step_length_m": {},
    }

    hip_base_x_m = cfg.speed_m_s * time_s
    for side in SIDES:
        sway_sign = 1.0 if side == "L" else -1.0
        hip_x = hip_base_x_m + cfg.hip_sway_m * sway_sign * np.sin(
            2 * np.pi * time_s / stride_time_s
        )
        hip_y = cfg.hip_height_m + 0.02 * np.sin(4 * np.pi * time_s / stride_time_s)
        keypoints_m[sided("hip", side)] = np.column_stack([hip_x, hip_y])

        first_hs_s = cfg.first_hs_s(side)
        stance_pct = cfg.stance_pct(side)
        stance_time_s = stance_pct / 100.0 * stride_time_s
        swing_time_s = stride_time_s - stance_time_s
        # Plant the foot so that the heel is HEEL_AHEAD_AT_CONTACT_M in front of the mid-hip
        # at every heel strike, and so that the step length is the true fraction of the stride.
        x0_m = cfg.speed_m_s * first_hs_s + HEEL_AHEAD_AT_CONTACT_M

        heel_x = _foot_x_m(
            time_s,
            first_hs_s,
            stride_time_s,
            stance_time_s,
            cfg.stride_length_m,
            x0_m,
            cfg.heel_initial_slope,
            cfg.heel_terminal_slope,
        )
        toe_x = cfg.foot_length_m + _foot_x_m(
            time_s,
            first_hs_s,
            stride_time_s,
            stance_time_s,
            cfg.stride_length_m,
            x0_m,
            cfg.toe_initial_slope,
            cfg.toe_terminal_slope,
        )
        phase = ((time_s - first_hs_s) / stride_time_s) % 1.0
        swing_u = np.clip((phase - stance_pct / 100.0) * stride_time_s / swing_time_s, 0.0, 1.0)
        lift = cfg.swing_height_m * np.sin(np.pi * swing_u)
        keypoints_m[sided("heel", side)] = np.column_stack([heel_x, lift])
        keypoints_m[sided("big_toe", side)] = np.column_stack([toe_x, 0.6 * lift])
        keypoints_m[sided("ankle", side)] = np.column_stack([0.5 * (heel_x + toe_x), 0.08 + lift])
        keypoints_m[sided("knee", side)] = np.column_stack(
            [0.5 * (hip_x + heel_x), 0.5 * cfg.hip_height_m + 0.3 * lift]
        )

        peak_stance_deg = cfg.peak_knee_stance_deg(side)
        peak_swing_deg = cfg.peak_knee_swing_deg(side)
        angles[sided("knee_flexion_deg", side)] = knee_curve_deg(
            phase, cfg.base_knee_deg, peak_stance_deg, peak_swing_deg
        )
        angles[sided("hip_flexion_deg", side)] = hip_curve_deg(
            phase, cfg.hip_mean_deg, cfg.hip_amplitude_deg
        )

        k = np.arange(-2, cfg.n_cycles + 3)
        hs_times = first_hs_s + k * stride_time_s
        to_times = hs_times + stance_time_s
        margin_s = 0.05 * stride_time_s
        hs_times = hs_times[(hs_times >= margin_s) & (hs_times <= time_s[-1] - margin_s)]
        to_times = to_times[(to_times >= margin_s) & (to_times <= time_s[-1] - margin_s)]

        truth["hs_frames"][side] = np.round(hs_times * fps).astype(int)
        truth["to_frames"][side] = np.round(to_times * fps).astype(int)
        truth["hs_times"][side] = hs_times
        truth["to_times"][side] = to_times
        truth["stance_pct"][side] = stance_pct
        truth["stance_time_s"][side] = stance_time_s
        truth["swing_time_s"][side] = swing_time_s
        truth["peak_stance"][side] = peak_stance_deg
        truth["peak_swing"][side] = peak_swing_deg
        truth["knee_curve"][side] = knee_curve_deg(
            phase_grid, cfg.base_knee_deg, peak_stance_deg, peak_swing_deg
        )

    # Side-less channel, exercises the base-channel path in cycles.py.
    trunk_phase = ((time_s - cfg.first_hs_s("L")) / stride_time_s) % 1.0
    angles["trunk_lean_deg"] = 3.0 + np.sin(4 * np.pi * trunk_phase)

    if cfg.noise_deg:
        for name, series in angles.items():
            angles[name] = series + rng.normal(0.0, cfg.noise_deg, n_frames)

    keypoints: dict[str, np.ndarray] = {}
    # Keypoint noise is always specified in pixels of the nominal camera and converted
    # to metres, so that "px" and "m" output carry the same physical noise level.
    noise_m = cfg.noise_px / cfg.pixels_per_m
    for name, arr in keypoints_m.items():
        xy = arr.copy()
        if noise_m:
            xy = xy + rng.normal(0.0, noise_m, xy.shape)
        xy[:, 0] *= direction_sign
        xy = xy * scale
        if cfg.unit == "m":
            z = np.full(n_frames, -0.1 if name.endswith("_L") else 0.1)
            keypoints[name] = np.column_stack([xy[:, 0], xy[:, 1], z])
        else:
            keypoints[name] = xy

    if cfg.nan_gaps_s:
        blanked = cfg.nan_channels or (tuple(angles) + tuple(keypoints))
        for name in blanked:
            mask = np.zeros(n_frames, dtype=bool)
            for start_s, end_s in cfg.nan_gaps_s:
                mask |= (time_s >= start_s) & (time_s < end_s)
            if name in angles:
                series = angles[name].copy()
                series[mask] = np.nan
                angles[name] = series
            if name in keypoints:
                arr = keypoints[name].copy()
                arr[mask, :] = np.nan
                keypoints[name] = arr

    confidence: dict[str, np.ndarray] = {}
    for name in keypoints:
        level = cfg.confidence
        far_side = (
            cfg.confidence_far_side is not None
            and cfg.camera_near_side is not None
            and not name.endswith(f"_{cfg.camera_near_side}")
        )
        if far_side:
            level = float(cfg.confidence_far_side)
        confidence[name] = np.full(n_frames, level, dtype=float)

    result = KinematicsResult(
        backend="synthetic",
        fps=fps,
        time_s=time_s,
        angles_deg=angles,
        keypoints=keypoints,
        keypoint_unit="m" if cfg.unit == "m" else "px",
        confidence=confidence,
        walking_direction=cfg.direction if cfg.declare_direction else "unknown",
        camera_near_side=cfg.camera_near_side,
        meta={"generator": "tests.core.synthetic"},
    )
    result.validate()

    offset = cfg.right_offset_pct / 100.0
    truth_obj = SyntheticTruth(
        fps=fps,
        stride_time_s=stride_time_s,
        heel_strikes=truth["hs_frames"],
        toe_offs=truth["to_frames"],
        heel_strike_times_s=truth["hs_times"],
        toe_off_times_s=truth["to_times"],
        stance_pct=truth["stance_pct"],
        swing_pct={s: 100.0 - truth["stance_pct"][s] for s in SIDES},
        stance_time_s=truth["stance_time_s"],
        swing_time_s=truth["swing_time_s"],
        step_time_s={"L": (1.0 - offset) * stride_time_s, "R": offset * stride_time_s},
        step_length_m={
            "L": (1.0 - offset) * cfg.stride_length_m,
            "R": offset * cfg.stride_length_m,
        },
        double_support_pct=truth["stance_pct"]["L"] + truth["stance_pct"]["R"] - 100.0,
        cadence_steps_per_min=120.0 / stride_time_s,
        stride_length_m=cfg.stride_length_m,
        walking_speed_m_s=cfg.speed_m_s,
        peak_knee_stance_deg=truth["peak_stance"],
        peak_knee_swing_deg=truth["peak_swing"],
        knee_curve_deg=truth["knee_curve"],
    )
    return result, truth_obj

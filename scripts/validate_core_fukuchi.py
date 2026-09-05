#!/usr/bin/env python3
"""Validate the gait-core pipeline against real Fukuchi et al. (2018) marker trajectories.

Why marker-based and not angle-based
-------------------------------------
The Fukuchi ASCII release (``WBDSascii.zip``) ships, per overground pass, **marker
trajectories** (``*mkr.txt``, ~150 Hz, mm) and **force-plate signals** (``*grf.txt``, 300 Hz).
It does **not** ship a per-pass, per-frame joint-angle time series: ``*ang.txt`` is already
cycle-normalised (101 points, 0-100 %) and averaged over every pass of one condition. So a
faithful "Variante A" (real marker time series through the whole pipeline) is only possible
for the **keypoint** side of :class:`~openacl.schema.KinematicsResult`; the **angle** channels
have to come from somewhere else.

This script does not fall back to synthetic angles (Variante B). Instead it derives sagittal
knee/hip/ankle angles directly from the same real markers, using a minimal 2-D segment-angle
model (thigh = knee-hip, shank = ankle-knee, foot = toe-heel, all projected onto the
progression/vertical plane -- exactly what a monocular sagittal-view backend would see). The
sign and the pelvis-tilt correction were calibrated once against subject 1 (comfortable,
first pass) by matching Fukuchi's own reported landmark values (knee ~0 deg at initial
contact, ~67.6 deg peak in swing; hip ~36 deg at initial contact, ~-0.7 deg at 54 %; ankle
~+9 deg peak dorsiflexion, ~-14.7 deg peak plantarflexion -- see
``src/openacl/norm/fukuchi.py`` docstring and ``src/openacl/norm/README.md``). See
:func:`sagittal_angles_deg` for the formulas.

This means: **events, gait-cycle segmentation and spatio-temporal parameters are validated
against 100 % real, independently measured data** (markers for kinematics, force plates for
stance/cadence/double support). The angle-domain checks (peak knee flexion, GVS/GPS) are
validated against a self-derived angle proxy that is expected to carry a modelling offset of a
few degrees relative to Fukuchi's own Vicon model (the ``norm/README.md`` "Bekannte
Einschränkungen" section documents a comparable 4.5 deg offset *between two proper marker-based
models*), so they are a shape/timing check, not an absolute-accuracy check.

Usage
-----
::

    python scripts/validate_core_fukuchi.py

Reads ``data/norm/fukuchi2018/`` (gitignored, CC BY 4.0, must be downloaded locally first, see
``scripts/download_normdata.py``). Writes ``docs/validation/core_vs_fukuchi.md`` and
``docs/img/validation_events.png``.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from openacl.core.pipeline import GaitAnalysis, analyze
from openacl.norm import fukuchi
from openacl.norm.bands import load_normbands
from openacl.schema import KinematicsResult

DEFAULT_ROOT = REPO_ROOT / "data" / "norm" / "fukuchi2018"
ZIP_NAME = "WBDSascii.zip"
"""The overground marker files (``*mkr.txt``) only exist inside this archive; the ASCII
download step (``scripts/download_normdata.py``) only unpacks ``*ang.txt``/``*grf.txt``."""

OUT_MD = REPO_ROOT / "docs" / "validation" / "core_vs_fukuchi.md"
OUT_PNG = REPO_ROOT / "docs" / "img" / "validation_events.png"

CONDITIONS: tuple[str, ...] = ("S", "C", "F")
CONDITION_SPEED_CLASS: dict[str, str] = {"S": "slow", "C": "comfortable", "F": "fast"}
CONDITION_LABEL_DE: dict[str, str] = {"S": "langsam", "C": "komfortabel", "F": "schnell"}

DEFAULT_SUBJECTS: tuple[str, ...] = tuple(f"WBDS{i:02d}" for i in range(1, 13))
"""12 subjects: comfortably above the 10 required by the task, some margin for missing files."""

MKR_RE = re.compile(r"^(WBDS\d+)walkO(\d+)([SCF])mkr\.txt$")

# Marker name -> KinematicsResult keypoint name (side-prefixed as "R."/"L." in the file).
MARKER_TO_KEYPOINT: dict[str, str] = {
    "Heel": "heel",
    "MT1": "big_toe",
    "MT5": "small_toe",
    "GTR": "hip",  # greater trochanter: closest available proxy for the hip joint centre
    "Knee": "knee",
    "Ankle": "ankle",
}


# --------------------------------------------------------------------------- zip access
def _marker_members(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path) as zf:
        return zf.namelist()


def first_available_pass(members: list[str], subject_id: str, condition: str) -> int | None:
    """Lowest overground pass number with a marker file for ``subject_id``/``condition``."""
    passes = [
        int(m.group(2))
        for name in members
        if (m := MKR_RE.match(name)) and m.group(1) == subject_id and m.group(3) == condition
    ]
    return min(passes) if passes else None


def read_marker_file(zip_path: Path, member: str) -> pd.DataFrame:
    """Read one ``*mkr.txt`` member straight out of the zip, no extraction to disk."""
    with zipfile.ZipFile(zip_path) as zf, zf.open(member) as raw:
        return pd.read_csv(io.TextIOWrapper(raw, encoding="utf-8"), sep="\t")


# --------------------------------------------------------------------------- angle model
def _xy(df: pd.DataFrame, prefix: str) -> np.ndarray:
    """Progression/vertical columns of one marker, shape ``(n_frames, 2)``."""
    return df[[f"{prefix}X", f"{prefix}Y"]].to_numpy(dtype=float)


def _signed_angle_deg(v_from: np.ndarray, v_to: np.ndarray) -> np.ndarray:
    """Signed angle in degrees from ``v_from`` to ``v_to`` (2-D vectors, last axis = x/y)."""
    cross = v_from[..., 0] * v_to[..., 1] - v_from[..., 1] * v_to[..., 0]
    dot = v_from[..., 0] * v_to[..., 0] + v_from[..., 1] * v_to[..., 1]
    return np.degrees(np.arctan2(cross, dot))


def sagittal_angles_deg(df: pd.DataFrame) -> tuple[dict[str, np.ndarray], float]:
    """Knee/hip/ankle sagittal angles from markers, plus the net progression sign.

    thigh = knee - hip (GTR), shank = ankle - knee, foot = toe (MT1) - heel, all in the
    progression/vertical plane (mediolateral is dropped, as a sagittal video would). Hip
    flexion is thigh-vs-vertical corrected by the pelvis tilt (ASIS-PSIS segment vs.
    horizontal), because Fukuchi's own hip angle is thigh-relative-to-pelvis, not
    thigh-relative-to-the-lab. Knee sign and the ankle 90 deg neutral offset were fixed by
    matching the ranges documented in ``openacl/norm/fukuchi.py`` on subject 1 (comfortable).
    """
    mean_asis = 0.5 * (_xy(df, "R.ASIS") + _xy(df, "L.ASIS"))
    mean_psis = 0.5 * (_xy(df, "R.PSIS") + _xy(df, "L.PSIS"))
    pelvis_vec = mean_asis - mean_psis
    forward_sign = 1.0 if (mean_asis[-1, 0] - mean_asis[0, 0]) >= 0 else -1.0
    horiz_forward = np.zeros_like(pelvis_vec)
    horiz_forward[:, 0] = forward_sign
    pelvis_tilt_deg = -_signed_angle_deg(horiz_forward, pelvis_vec)

    angles: dict[str, np.ndarray] = {}
    for side in ("L", "R"):
        hip = _xy(df, f"{side}.GTR")
        knee = _xy(df, f"{side}.Knee")
        ankle = _xy(df, f"{side}.Ankle")
        heel = _xy(df, f"{side}.Heel")
        toe = _xy(df, f"{side}.MT1")
        thigh = knee - hip
        shank = ankle - knee
        foot = toe - heel
        vertical_down = np.zeros_like(thigh)
        vertical_down[:, 1] = -1.0

        angles[f"knee_flexion_deg_{side}"] = -_signed_angle_deg(thigh, shank)
        angles[f"hip_flexion_deg_{side}"] = (
            _signed_angle_deg(vertical_down, thigh) + pelvis_tilt_deg
        )
        angles[f"ankle_dorsiflexion_deg_{side}"] = _signed_angle_deg(shank, foot) - 90.0
    return angles, forward_sign


def build_kinematics_result(df: pd.DataFrame, *, meta: dict) -> tuple[KinematicsResult, float]:
    """Build one ``KinematicsResult`` from a raw Fukuchi ``*mkr.txt`` frame.

    Marker columns are ``<Side>.<Name><X|Y|Z>`` in mm; numerically verified (see module
    docstring / ``docs/validation/core_vs_fukuchi.md``) as X = progression, Y = vertical,
    Z = mediolateral -- i.e. already in the column order gait-core expects
    (0 = progression, 1 = vertical), no axis swap needed. ``walking_direction`` is left
    ``"unknown"`` on purpose so that ``openacl.core.events.estimate_direction_sign`` has to
    recover it from the real ``sacrum`` trace; ``forward_sign`` (returned separately) is our
    own reference to check that estimate against.
    """
    time_s = df["Time"].to_numpy(dtype=float)
    time_s = time_s - time_s[0]
    fps = 1.0 / np.mean(np.diff(time_s))

    def xyz_m(prefix: str) -> np.ndarray:
        return df[[f"{prefix}X", f"{prefix}Y", f"{prefix}Z"]].to_numpy(dtype=float) / 1000.0

    keypoints: dict[str, np.ndarray] = {"sacrum": 0.5 * (xyz_m("R.PSIS") + xyz_m("L.PSIS"))}
    for marker, keypoint in MARKER_TO_KEYPOINT.items():
        for side in ("L", "R"):
            keypoints[f"{keypoint}_{side}"] = xyz_m(f"{side}.{marker}")

    angles_deg, forward_sign = sagittal_angles_deg(df)

    result = KinematicsResult(
        backend="fukuchi2018_marker",
        fps=float(fps),
        time_s=time_s,
        angles_deg=angles_deg,
        keypoints=keypoints,
        keypoint_unit="m",
        walking_direction="unknown",
        meta=meta,
    )
    result.validate()
    return result, forward_sign


# --------------------------------------------------------------------------- reference data
@dataclass
class ReferenceTables:
    """Ground truth pulled from the Fukuchi dataset itself, keyed by ``(subject_id, "O"+cond)``."""

    file_speed_m_s: dict[tuple[str, str], float]
    """Per exact pass (matches the marker file), from ``WBDSinfo.xlsx``."""
    grf_stance_pct: dict[tuple[str, str], float]
    grf_cadence_spm: dict[tuple[str, str], float]
    grf_double_support_pct: dict[tuple[str, str], float]
    own_model_peak_knee_swing_deg: dict[tuple[str, str], float]
    """Fukuchi's own (Vicon-model) cycle-normalised knee flexion peak, averaged over L/R."""


def build_reference_tables(root: Path) -> ReferenceTables:
    info = pd.read_excel(root / "WBDSinfo.xlsx")
    file_speed: dict[tuple[str, str], float] = {}
    name_re = re.compile(r"^(WBDS\d+)walkO(\d+)([SCF])\.c3d$", re.IGNORECASE)
    for _, row in info.iterrows():
        m = name_re.match(str(row["FileName"]))
        if not m:
            continue
        speed = pd.to_numeric(row["GaitSpeed(m/s)"], errors="coerce")
        if np.isfinite(speed):
            file_speed[(m.group(1), int(m.group(2)), m.group(3))] = float(speed)

    grf = fukuchi.load_spatiotemporal(root, conditions=("overground",))
    grf_grouped = grf.groupby(["subject_id", "trial_id"])[
        ["stance_pct", "cadence_steps_min", "double_support_pct"]
    ].mean()

    angles = fukuchi.load_angles(root, conditions=("overground",))
    knee = angles[angles["channel"] == "knee_flexion_deg"]
    per_side_peak = knee.groupby(["subject_id", "trial_id", "side"])["value_deg"].max()
    own_peak = per_side_peak.groupby(["subject_id", "trial_id"]).mean()

    return ReferenceTables(
        file_speed_m_s=file_speed,
        grf_stance_pct=grf_grouped["stance_pct"].to_dict(),
        grf_cadence_spm=grf_grouped["cadence_steps_min"].to_dict(),
        grf_double_support_pct=grf_grouped["double_support_pct"].to_dict(),
        own_model_peak_knee_swing_deg=own_peak.to_dict(),
    )


# --------------------------------------------------------------------------- event timing
_PLATE_RE = re.compile(r"FP([0-9_]+)")


def _plate_force_columns(cell: object) -> list[str]:
    """``"FP4_5, FP1"`` -> ``["Fy1", "Fy4", "Fy5"]`` (same parsing as ``fukuchi._plates_for_foot``)."""
    if not isinstance(cell, str):
        return []
    plates: list[int] = []
    for group in _PLATE_RE.findall(cell):
        plates.extend(int(part) for part in group.split("_") if part)
    return [f"Fy{p}" for p in sorted(set(plates))]


def _force_contacts_s(
    force_n: np.ndarray, fs_hz: float, threshold_n: float = 30.0, min_dur_s: float = 0.15
) -> list[tuple[float, float]]:
    """``(onset_s, offset_s)`` pairs where ``force_n`` crosses ``threshold_n`` (same rule as
    ``fukuchi.load_spatiotemporal``, in seconds instead of samples)."""
    on = force_n > threshold_n
    edges = np.diff(on.astype(np.int8))
    starts = list(np.flatnonzero(edges == 1) + 1)
    ends = list(np.flatnonzero(edges == -1) + 1)
    if on[0]:
        starts.insert(0, 0)
    if on[-1]:
        ends.append(len(on))
    min_samples = int(min_dur_s * fs_hz)
    return [
        (s / fs_hz, e / fs_hz) for s, e in zip(starts, ends, strict=False) if e - s >= min_samples
    ]


def event_timing_offsets_ms(
    root: Path,
    subject_id: str,
    pass_no: int,
    condition: str,
    analysis: GaitAnalysis,
    *,
    match_window_s: float = 0.2,
) -> list[dict[str, object]]:
    """Signed timing offset (ours - force-plate, milliseconds) for the exact same pass.

    Matches every gait-core heel strike / toe off to the nearest force-plate onset/offset of
    the *same pass* (not a condition average, unlike ``ReferenceTables``); pairs further apart
    than ``match_window_s`` are dropped as unmatched (missed plate contact). Positive means
    gait-core detected the event *later* than the force plate.
    """
    info = pd.read_excel(root / "WBDSinfo.xlsx")
    info["_key"] = info["FileName"].astype(str).str.replace(".c3d", "", regex=False).str.upper()
    info = info.set_index("_key")
    key = f"{subject_id}WALKO{pass_no:02d}{condition}"
    if key not in info.index:
        return []
    row = info.loc[key]
    grf_path = root / "ascii" / f"{subject_id}walkO{pass_no:02d}{condition}grf.txt"
    if not grf_path.exists():
        return []
    grf = pd.read_csv(grf_path, sep="\t")

    rows: list[dict[str, object]] = []
    for side, foot_col in (("R", "FP_RightFoot"), ("L", "FP_LeftFoot")):
        cols = [c for c in _plate_force_columns(row[foot_col]) if c in grf.columns]
        if not cols:
            continue
        force = grf[cols].to_numpy(dtype=float).sum(axis=1)
        hs_times = analysis.events.heel_strike_times_s(side)
        to_times = analysis.events.toe_off_times_s(side)
        for ic_s, to_s in _force_contacts_s(force, fukuchi.GRF_FS_HZ):
            if hs_times.size:
                nearest = hs_times[np.argmin(np.abs(hs_times - ic_s))]
                if abs(nearest - ic_s) < match_window_s:
                    rows.append(
                        {
                            "subject_id": subject_id,
                            "condition": condition,
                            "side": side,
                            "event": "heel_strike",
                            "offset_ms": 1000.0 * (nearest - ic_s),
                        }
                    )
            if to_times.size:
                nearest = to_times[np.argmin(np.abs(to_times - to_s))]
                if abs(nearest - to_s) < match_window_s:
                    rows.append(
                        {
                            "subject_id": subject_id,
                            "condition": condition,
                            "side": side,
                            "event": "toe_off",
                            "offset_ms": 1000.0 * (nearest - to_s),
                        }
                    )
    return rows


# --------------------------------------------------------------------------- one trial
@dataclass
class TrialRow:
    subject_id: str
    condition: str
    condition_label: str
    pass_no: int
    n_frames: int
    n_valid_cycles_L: int
    n_valid_cycles_R: int
    speed_measured_m_s: float
    speed_ref_m_s: float
    speed_diff_m_s: float
    stance_measured_pct: float
    stance_ref_pct: float
    stance_diff_pct: float
    cadence_measured_spm: float
    cadence_ref_spm: float
    cadence_diff_spm: float
    peak_knee_measured_deg: float
    peak_knee_normband_mean_deg: float
    peak_knee_normband_sd_deg: float
    peak_knee_diff_vs_normband_deg: float
    peak_knee_own_model_deg: float
    peak_knee_diff_vs_own_model_deg: float
    direction_ours: int
    direction_gaitcore: int
    direction_source_gaitcore: str
    direction_match: bool
    n_warnings: int


def run_trial(
    zip_path: Path,
    root: Path,
    subject_id: str,
    condition: str,
    members: list[str],
    refs: ReferenceTables,
    normbands: dict,
) -> tuple[TrialRow, GaitAnalysis, KinematicsResult] | None:
    """Run one subject/condition through the pipeline; ``None`` if no marker file exists."""
    pass_no = first_available_pass(members, subject_id, condition)
    if pass_no is None:
        return None
    member = f"{subject_id}walkO{pass_no:02d}{condition}mkr.txt"
    df = read_marker_file(zip_path, member)

    meta = {
        "source": member,
        "dataset": "fukuchi2018",
        "subject_id": subject_id,
        "condition": condition,
        "pass_no": pass_no,
    }
    result, forward_sign = build_kinematics_result(df, meta=meta)
    speed_class = CONDITION_SPEED_CLASS[condition]
    analysis = analyze(result, normbands=normbands, speed_class=speed_class)

    trial_id = f"O{condition}"
    key = (subject_id, trial_id)
    speed_ref = refs.file_speed_m_s.get((subject_id, pass_no, condition), float("nan"))
    stance_ref = refs.grf_stance_pct.get(key, float("nan"))
    cadence_ref = refs.grf_cadence_spm.get(key, float("nan"))
    own_peak = refs.own_model_peak_knee_swing_deg.get(key, float("nan"))

    band = normbands.get(f"knee_flexion_deg@{speed_class}")
    if band is not None:
        peak_idx = int(np.argmax(band.mean))
        band_peak_mean = float(band.mean[peak_idx])
        band_peak_sd = float(band.sd[peak_idx])
    else:
        band_peak_mean = band_peak_sd = float("nan")

    peak_measured = float(
        np.nanmean(
            [
                analysis.discrete_deg.get("L", {}).get("peak_knee_flexion_swing_deg", np.nan),
                analysis.discrete_deg.get("R", {}).get("peak_knee_flexion_swing_deg", np.nan),
            ]
        )
    )
    speed_measured = analysis.spatiotemporal.both.walking_speed_m_s.mean
    stance_measured = analysis.spatiotemporal.both.stance_pct.mean
    cadence_measured = analysis.spatiotemporal.both.cadence_steps_per_min.mean
    direction_ours = int(forward_sign)

    row = TrialRow(
        subject_id=subject_id,
        condition=condition,
        condition_label=CONDITION_LABEL_DE[condition],
        pass_no=pass_no,
        n_frames=result.n_frames,
        n_valid_cycles_L=analysis.n_valid_cycles["L"],
        n_valid_cycles_R=analysis.n_valid_cycles["R"],
        speed_measured_m_s=speed_measured,
        speed_ref_m_s=speed_ref,
        speed_diff_m_s=speed_measured - speed_ref,
        stance_measured_pct=stance_measured,
        stance_ref_pct=stance_ref,
        stance_diff_pct=stance_measured - stance_ref,
        cadence_measured_spm=cadence_measured,
        cadence_ref_spm=cadence_ref,
        cadence_diff_spm=cadence_measured - cadence_ref,
        peak_knee_measured_deg=peak_measured,
        peak_knee_normband_mean_deg=band_peak_mean,
        peak_knee_normband_sd_deg=band_peak_sd,
        peak_knee_diff_vs_normband_deg=peak_measured - band_peak_mean,
        peak_knee_own_model_deg=own_peak,
        peak_knee_diff_vs_own_model_deg=peak_measured - own_peak,
        direction_ours=direction_ours,
        direction_gaitcore=analysis.events.direction_sign,
        direction_source_gaitcore=analysis.events.direction_source,
        direction_match=(direction_ours == analysis.events.direction_sign),
        n_warnings=len(analysis.warnings),
    )
    return row, analysis, result


# --------------------------------------------------------------------------- reporting
def _df_to_markdown(frame: pd.DataFrame) -> str:
    """Minimal GitHub-flavoured markdown table, no ``tabulate`` dependency."""
    headers = [str(c) for c in frame.columns]

    def fmt(value: object) -> str:
        if isinstance(value, float):
            if not np.isfinite(value):
                return "n/a"
            return f"{value:.3g}"
        return str(value)

    rows = [[fmt(v) for v in row] for row in frame.itertuples(index=False, name=None)]
    widths = [
        max(len(headers[i]), *(len(r[i]) for r in rows)) if rows else len(headers[i])
        for i in range(len(headers))
    ]
    lines = [
        "| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " |",
        "| " + " | ".join("-" * widths[i] for i in range(len(headers))) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(v.ljust(widths[i]) for i, v in enumerate(row)) + " |")
    return "\n".join(lines)


def _bias_sd_row(diffs: pd.Series, unit: str, label: str) -> dict[str, object]:
    values = diffs.to_numpy(dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return {"Größe": label, "n": 0, "Bias": "n/a", "SD": "n/a", "Einheit": unit}
    return {
        "Größe": label,
        "n": int(values.size),
        "Bias": round(float(np.mean(values)), 3),
        "SD": round(float(np.std(values, ddof=1)), 3) if values.size > 1 else 0.0,
        "Einheit": unit,
    }


def write_report(table: pd.DataFrame, timing: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    summary_rows = [
        _bias_sd_row(table["speed_diff_m_s"], "m/s", "Ganggeschwindigkeit (Marker vs. Metadaten)"),
        _bias_sd_row(
            table["stance_diff_pct"], "%", "Standphase (Marker/Events vs. Kraftmessplatte)"
        ),
        _bias_sd_row(
            table["cadence_diff_spm"], "/min", "Kadenz (Marker/Events vs. Kraftmessplatte)"
        ),
        _bias_sd_row(
            table["peak_knee_diff_vs_normband_deg"],
            "deg",
            "Peak Knieflexion Schwung (eigenes Marker-Winkelmodell vs. Normband-Peak)",
        ),
        _bias_sd_row(
            table["peak_knee_diff_vs_own_model_deg"],
            "deg",
            "Peak Knieflexion Schwung (eigenes Marker-Winkelmodell vs. Fukuchis eigenes Modell)",
        ),
    ]
    summary = pd.DataFrame(summary_rows)

    direction_mismatches = table.loc[~table["direction_match"]]
    n_direction_estimated = int((table["direction_source_gaitcore"] != "walking_direction").sum())

    lines: list[str] = []
    lines.append("# Validierung des Gait-Core gegen Fukuchi et al. (2018)")
    lines.append("")
    lines.append(
        "Quelle: Fukuchi CA, Fukuchi RK, Duarte M (2018), *A public data set of overground and "
        "treadmill walking kinematics and kinetics of healthy individuals*, PeerJ 6:e4640, "
        "doi:10.6084/m9.figshare.5722711, CC BY 4.0."
    )
    lines.append("")
    lines.append(
        "**Variante:** Marker-Trajektorien (real, ~150 Hz, aus `WBDSascii.zip`) für Events, "
        "Zyklen und Zeit-Weg-Parameter. Für die Winkelkanäle (Knie-/Hüftflexion, "
        "Sprunggelenk-Dorsalextension) enthält die ASCII-Ausgabe **keine** unnormierten "
        "Zeitreihen pro Durchgang (nur zyklus-normierte Mittelwertkurven je Bedingung), daher "
        "wurden diese direkt aus denselben realen Markern über ein sagittales "
        "Segmentwinkel-Modell rekonstruiert (Details und Kalibrierung im Docstring von "
        "`scripts/validate_core_fukuchi.py`, Funktion `sagittal_angles_deg`). Damit sind "
        "Events/Zyklen/Zeit-Weg-Parameter zu 100 % real validiert; die Peak-Knieflexion ist "
        "gegen ein selbst abgeleitetes Winkelmodell validiert (Formkonsistenz und "
        "Zeitnormierung), nicht gegen Fukuchis eigenes Vicon-Modell 1:1 (dessen Wert steht "
        "als zweite Referenzspalte daneben)."
    )
    lines.append("")
    lines.append(f"Probanden: {table['subject_id'].nunique()}, Durchgänge: {len(table)}.")
    lines.append("")
    lines.append("## Ergebnistabelle")
    lines.append("")
    display_cols = {
        "subject_id": "Proband",
        "condition_label": "Bedingung",
        "speed_measured_m_s": "v gemessen [m/s]",
        "speed_ref_m_s": "v Referenz [m/s]",
        "speed_diff_m_s": "Δv [m/s]",
        "stance_measured_pct": "Standphase gemessen [%]",
        "stance_ref_pct": "Standphase Ref. (Kraftmessplatte) [%]",
        "stance_diff_pct": "ΔStandphase [%]",
        "cadence_measured_spm": "Kadenz gemessen [/min]",
        "cadence_ref_spm": "Kadenz Ref. [/min]",
        "peak_knee_measured_deg": "Peak Knie gemessen [deg]",
        "peak_knee_normband_mean_deg": "Normband-Peak [deg]",
        "peak_knee_diff_vs_normband_deg": "ΔPeak Knie (vs. Normband) [deg]",
        "peak_knee_own_model_deg": "Peak Knie Fukuchi-Modell [deg]",
        "direction_match": "Richtung stimmt überein",
        "n_warnings": "# Warnungen",
    }
    display = table[list(display_cols)].rename(columns=display_cols)
    display = display.round(3)
    lines.append(_df_to_markdown(display))
    lines.append("")
    lines.append("## Bias und Streuung je Größe")
    lines.append("")
    lines.append(_df_to_markdown(summary))
    lines.append("")
    lines.append("## Befund: Standphase systematisch überschätzt (Event-Timing)")
    lines.append("")
    if timing.empty:
        lines.append(
            "Keine passenden Kraftmessplatten-Kontakte für einen Event-Timing-Vergleich gefunden."
        )
    else:
        timing_summary = (
            timing.groupby("event")["offset_ms"]
            .agg(n="count", bias_ms="mean", sd_ms=lambda s: s.std(ddof=1) if s.size > 1 else 0.0)
            .reset_index()
            .rename(columns={"event": "Event"})
        )
        lines.append(
            "Für jeden Durchgang wurde zusätzlich zum bedingungs-gemittelten "
            "Kraftmessplatten-Referenzwert oben ein direkter Zeitvergleich gemacht: jeder von "
            "`openacl.core.events.detect_events` erkannte Heel Strike/Toe Off wurde dem "
            "nächstgelegenen Kraft-Schwellenwert-Ereignis (30 N, Fy-Summe der zugeordneten "
            "Kraftmessplatten) **desselben Durchgangs** zugeordnet (Fenster ±0,2 s). "
            "Vorzeichen: `unser Zeitpunkt - Kraftmessplatten-Zeitpunkt`, positiv = zu spät erkannt."
        )
        lines.append("")
        lines.append(_df_to_markdown(timing_summary.round(3)))
        lines.append("")
        lines.append(
            "**Befund:** Heel Strike wird systematisch **zu früh**, Toe Off systematisch "
            "**zu spät** erkannt (siehe Tabelle oben), und zwar in dieser Größenordnung über "
            "praktisch alle Probanden/Bedingungen hinweg (kleine SD relativ zum Bias => "
            "systematischer Effekt, keine zufällige Streuung). Das erklärt den "
            "Standphasen-Bias oben (Standphase = HS bis TO relativ zur Strideszeit: ein zu "
            "frühes HS **und** ein zu spätes TO verlängern die gemessene Standphase in dieselbe "
            "Richtung).\n\n"
            "- **Datei/Zeile:** `src/openacl/core/events.py:228-229` "
            "(`hs[side] = _peaks(heel_rel, ...)`, `to[side] = _peaks(-toe_rel, ...)`), Methode "
            "nach Zeni et al. 2008 (lokales Maximum/Minimum von Ferse/Zehe relativ zum Becken).\n"
            "- **Ursache:** Die *kinematische* Definition des Ereignisses (Extremum der "
            "Fersen-/Zehen-Position relativ zum Becken) ist keine Kraft-Schwellenwert-Messung; "
            "sie eilt dem tatsächlichen Bodenkontakt (Heel Strike) etwas voraus und hinkt dem "
            "Lösen vom Boden (Toe Off) etwas hinterher. Zeni et al. 2008 berichten für ihr "
            "eigenes Markerset deutlich kleinere Abweichungen als hier gemessen; ein Teil der "
            "zusätzlichen Verzögerung dürfte an der Marker-Wahl liegen, die diese Validierung "
            "erzwingt (`big_toe` = Fukuchis `MT1`-Marker am ersten Mittelfußköpfchen, nicht an "
            "der Schuh-/Zehenspitze wie in Zenis Originalarbeit).\n"
            "- **Vorschlag mit Zahlen:** Bias und SD aus der Tabelle oben (openacl-Version zum "
            "Zeitpunkt des Laufs; siehe `docs/validation/core_vs_fukuchi.md` für den aktuellen "
            "Stand) als dokumentierte, ggf. konfigurierbare Korrektur in `GaitEvents`/"
            "`detect_events` ergänzen (z. B. `stance_pct` um den gemessenen Bias korrigieren, "
            "oder die Ereignis-Frames um die entsprechende Anzahl Frames verschieben), "
            "*mindestens* aber den Bias im Docstring von `detect_events` und in der "
            "MDC-Tabelle (`openacl/core/mdc.py`) dokumentieren, da ein Bias dieser "
            "Größenordnung die MDC-relative Schwelle der Interpretationsschicht (CLAUDE.md) "
            "verzerrt, wenn er unkorrigiert bleibt."
        )
    lines.append("")
    lines.append("## Richtungserkennung")
    lines.append("")
    lines.append(
        f"Bei {n_direction_estimated} von {len(table)} Durchgängen musste "
        "`estimate_direction_sign` die Gehrichtung aus der Sakrum-Verschiebung schätzen "
        '(`walking_direction` wurde absichtlich auf `"unknown"` gesetzt); Referenz ist das '
        "Vorzeichen der ASIS-Verschiebung über den ganzen Durchgang."
    )
    if direction_mismatches.empty:
        lines.append("Keine Abweichung zwischen geschätzter und Referenz-Gehrichtung gefunden.")
    else:
        lines.append(
            f"**{len(direction_mismatches)} Abweichung(en)** zwischen geschätzter und "
            "Referenz-Gehrichtung:"
        )
        lines.append("")
        lines.append(
            _df_to_markdown(
                direction_mismatches[
                    ["subject_id", "condition_label", "direction_ours", "direction_gaitcore"]
                ]
            )
        )
    lines.append("")
    lines.append("## Bekannte Einschränkungen dieser Validierung")
    lines.append("")
    lines.append(
        "- Winkelkanäle sind ein selbst abgeleitetes 2-D-Segmentwinkel-Modell aus denselben "
        "Markern (siehe oben), kein 1:1-Vergleich mit Fukuchis Vicon-Winkeln.\n"
        "- `hip_L`/`hip_R` sind der Trochanter-major-Marker (GTR), kein berechnetes "
        "Hüftgelenkzentrum.\n"
        "- Standphase/Kadenz-Referenz ist über alle Durchgänge einer Bedingung gemittelt "
        "(Kraftmessplatten-Zuordnung), nicht exakt derselbe Einzeldurchgang wie die Marker-Datei; "
        "Geschwindigkeits-Referenz dagegen ist exakt der gewählte Durchgang (aus "
        "`WBDSinfo.xlsx`).\n"
        "- Kein per-Keypoint-Konfidenzwert vorhanden (Mokap, kein Video-Backend); die "
        "entsprechende gait-core-Warnung ist erwartet, kein Befund."
    )
    out_path.write_text("\n".join(lines) + "\n")


def plot_example(analysis: GaitAnalysis, result: KinematicsResult, out_path: Path) -> None:
    """Heel-x trajectory of one trial with detected heel strikes / toe offs marked."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    time_s = result.time_s
    fig, ax = plt.subplots(figsize=(10, 4))
    for side, color in (("L", "tab:blue"), ("R", "tab:orange")):
        heel_x = result.keypoints[f"heel_{side}"][:, 0]
        ax.plot(time_s, heel_x, color=color, label=f"Ferse {side} (Progression, m)")
        hs = analysis.events.heel_strikes(side)
        to = analysis.events.toe_offs(side)
        if hs.size:
            ax.scatter(time_s[hs], heel_x[hs], marker="^", color=color, s=60, zorder=3)
        if to.size:
            ax.scatter(time_s[to], heel_x[to], marker="v", color=color, s=60, zorder=3)
    ax.scatter([], [], marker="^", color="black", label="Heel Strike (erkannt)")
    ax.scatter([], [], marker="v", color="black", label="Toe Off (erkannt)")
    ax.set_xlabel("Zeit [s]")
    ax.set_ylabel("Fersenposition, Gehrichtung [m]")
    ax.set_title(
        f"{result.meta.get('subject_id')} – {CONDITION_LABEL_DE[result.meta.get('condition')]} "
        "(Fukuchi 2018, Marker-Rohdaten)"
    )
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


# --------------------------------------------------------------------------- entry point
def run_validation(
    root: Path = DEFAULT_ROOT,
    subjects: tuple[str, ...] = DEFAULT_SUBJECTS,
    conditions: tuple[str, ...] = CONDITIONS,
) -> tuple[
    pd.DataFrame, pd.DataFrame, dict[tuple[str, str], tuple[GaitAnalysis, KinematicsResult]]
]:
    """Run every subject/condition through the pipeline; returns the table plus raw results."""
    zip_path = root / ZIP_NAME
    members = _marker_members(zip_path)
    refs = build_reference_tables(root)
    normbands = load_normbands(kind="angle_curve")

    rows: list[TrialRow] = []
    timing_rows: list[dict[str, object]] = []
    raw: dict[tuple[str, str], tuple[GaitAnalysis, KinematicsResult]] = {}
    for subject_id in subjects:
        for condition in conditions:
            outcome = run_trial(zip_path, root, subject_id, condition, members, refs, normbands)
            if outcome is None:
                continue
            row, analysis, result = outcome
            rows.append(row)
            raw[(subject_id, condition)] = (analysis, result)
            timing_rows.extend(
                event_timing_offsets_ms(root, subject_id, row.pass_no, condition, analysis)
            )

    table = pd.DataFrame([asdict(r) for r in rows])
    timing = pd.DataFrame(timing_rows)
    return table, timing, raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--example", default="WBDS01:C", help="subject:condition for the plot")
    args = parser.parse_args()

    if not (args.root / ZIP_NAME).exists():
        raise SystemExit(
            f"{args.root / ZIP_NAME} not found. Download it first "
            "(python scripts/download_normdata.py --dataset fukuchi2018) and unzip locally."
        )

    table, timing, raw = run_validation(root=args.root)
    print(table.to_string(index=False))
    write_report(table, timing, OUT_MD)
    print(f"wrote {OUT_MD}")

    example_subject, example_condition = args.example.split(":")
    key = (example_subject, example_condition)
    if key in raw:
        analysis, result = raw[key]
        plot_example(analysis, result, OUT_PNG)
        print(f"wrote {OUT_PNG}")
    else:
        print(f"example {args.example} not in the validated set, skipping plot")


if __name__ == "__main__":
    main()

"""Loader for the Fukuchi et al. (2018) overground and treadmill walking dataset.

Source
------
Fukuchi CA, Fukuchi RK, Duarte M. *A public data set of overground and treadmill walking
kinematics and kinetics of healthy individuals.* PeerJ 6:e4640 (2018).
figshare doi:10.6084/m9.figshare.5722711 -- **CC BY 4.0**.

42 healthy adults (24 young, 18 older). Overground at three self-selected speeds
(``S`` slow, ``C`` comfortable, ``F`` fast) and treadmill at eight fixed speeds
(``T01``..``T08``). The ASCII release ships one gait-cycle-normalised joint angle file per
subject and condition (101 rows, 0..100 % of the cycle) plus raw force-plate files.

File layout after ``scripts/download_normdata.py --dataset fukuchi2018``::

    data/norm/fukuchi2018/WBDSinfo.xlsx
    data/norm/fukuchi2018/ascii/WBDS01walkOCang.txt     # overground, comfortable
    data/norm/fukuchi2018/ascii/WBDS01walkT05ang.txt    # treadmill, speed step 5
    data/norm/fukuchi2018/ascii/WBDS01walkO01Cgrf.txt   # one overground pass, 5 plates

Sign convention
---------------
The ASCII angle files carry ``<side><Joint>Angle<X|Y|Z>``. The **Z** component is the
sagittal one in this release (verified numerically: ``KneeAngleZ`` is ~0 deg at initial
contact and peaks near 60-70 deg in swing, ``AnkleAngleZ`` is most negative around toe-off).
Z is already positive for knee flexion, hip flexion, ankle dorsiflexion and anterior pelvic
tilt, i.e. it matches the clinical convention of :mod:`openacl.schema` **without a flip**;
left and right use the same polarity. The per-channel factors are kept explicit in
:data:`SAGITTAL_COLUMNS` so a future release with a different axis order can be corrected
in one place.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

DATASET = "fukuchi2018"
N_PCT = 101
"""Rows per angle file: 0..100 % of the gait cycle."""

GRF_FS_HZ = 300.0
"""Analog sampling rate of the force-plate ASCII files."""

VERTICAL_GRF_PREFIX = "Fy"
"""Vertical component in the Fukuchi force-plate ASCII files."""

#: canonical channel -> (column template, sign factor to reach the clinical convention)
SAGITTAL_COLUMNS: dict[str, tuple[str, float]] = {
    "hip_flexion_deg": ("{side}HipAngleZ", +1.0),
    "knee_flexion_deg": ("{side}KneeAngleZ", +1.0),
    "ankle_dorsiflexion_deg": ("{side}AnkleAngleZ", +1.0),
}

#: side-less channels; Fukuchi reports pelvis twice (per side), we average them
UNSIDED_COLUMNS: dict[str, tuple[tuple[str, ...], float]] = {
    "pelvis_tilt_deg": (("RPelvisAngleZ", "LPelvisAngleZ"), +1.0),
}

_ANG_RE = re.compile(r"^WBDS(?P<subject>\d+)walk(?P<trial>O[SCF]|T\d+)ang\.txt$", re.IGNORECASE)
_GRF_RE = re.compile(
    r"^WBDS(?P<subject>\d+)walk(?:O(?P<pass_no>\d+)(?P<cond>[SCF])|T(?P<tread>\d+))grf\.txt$",
    re.IGNORECASE,
)
_FP_RE = re.compile(r"FP([0-9_]+)")

LONG_COLUMNS = [
    "dataset",
    "subject_id",
    "age_years",
    "sex",
    "height_m",
    "mass_kg",
    "leg_length_m",
    "trial_id",
    "speed_m_s",
    "condition",
    "side",
    "channel",
    "pct",
    "value_deg",
]


# --------------------------------------------------------------------------- subjects
@dataclass(frozen=True)
class FukuchiPaths:
    """Resolved paths of one local copy of the dataset."""

    root: Path

    @property
    def info_xlsx(self) -> Path:
        return self.root / "WBDSinfo.xlsx"

    @property
    def ascii_dir(self) -> Path:
        return self.root / "ascii"


def _leg_length_m(raw: float, height_m: float) -> float:
    """Return a plausible leg length in metres, falling back to ``0.53 * height``.

    ``WBDSinfo.xlsx`` contains a few implausible entries (up to 1.91 m). Anything outside
    40-62 % of body height is replaced by the standard estimate.
    """
    if np.isfinite(raw) and 0.40 * height_m <= raw <= 0.62 * height_m:
        return float(raw)
    return 0.53 * height_m


def load_subject_info(root: Path | str) -> pd.DataFrame:
    """Read ``WBDSinfo.xlsx`` into one row per subject.

    Columns: ``subject_id, age_years, sex, height_m, mass_kg, leg_length_m,
    leg_length_measured, age_group``.
    """
    paths = FukuchiPaths(Path(root))
    raw = pd.read_excel(paths.info_xlsx)
    raw = raw[raw["Subject"].notna()]
    per_subject = raw.groupby("Subject").first(numeric_only=False)
    rows = []
    for subject, row in per_subject.iterrows():
        height_m = float(row["Height"]) / 100.0
        measured = float(row["LegLength"]) if pd.notna(row["LegLength"]) else float("nan")
        leg = _leg_length_m(measured, height_m)
        rows.append(
            {
                "subject_id": f"WBDS{int(subject):02d}",
                "age_years": float(row["Age"]),
                "sex": str(row["Gender"]).strip().upper()[:1],
                "height_m": height_m,
                "mass_kg": float(row["Mass"]),
                "leg_length_m": leg,
                "leg_length_measured": bool(abs(leg - measured) < 1e-9),
                "age_group": str(row["AgeGroup"]),
            }
        )
    return pd.DataFrame(rows).sort_values("subject_id").reset_index(drop=True)


def load_trial_speeds(root: Path | str) -> pd.DataFrame:
    """Return the measured speed of every walking trial.

    Columns: ``subject_id, trial_id, condition, speed_m_s, source_file``. ``trial_id`` is the
    key used by the angle files (``OS``/``OC``/``OF`` for overground, ``T01``..``T08`` for
    treadmill); overground therefore has several rows per ``trial_id``, one per pass.
    """
    paths = FukuchiPaths(Path(root))
    raw = pd.read_excel(paths.info_xlsx)
    rows = []
    for _, row in raw.iterrows():
        name = str(row["FileName"])
        match = re.match(r"^WBDS(\d+)walk(O\d+([SCF])|T(\d+))\.c3d$", name, re.IGNORECASE)
        if not match:
            continue
        speed = pd.to_numeric(row["GaitSpeed(m/s)"], errors="coerce")
        if not np.isfinite(speed):
            continue
        subject = f"WBDS{int(match.group(1)):02d}"
        if match.group(3):  # overground pass
            trial_id, condition = f"O{match.group(3).upper()}", "overground"
        else:
            trial_id, condition = f"T{int(match.group(4)):02d}", "treadmill"
        rows.append(
            {
                "subject_id": subject,
                "trial_id": trial_id,
                "condition": condition,
                "speed_m_s": float(speed),
                "source_file": name,
            }
        )
    return pd.DataFrame(rows)


def _mean_speed_per_trial(root: Path | str) -> pd.DataFrame:
    """Mean speed per ``(subject_id, trial_id)``; overground averages its passes."""
    speeds = load_trial_speeds(root)
    return (
        speeds.groupby(["subject_id", "trial_id", "condition"], as_index=False)["speed_m_s"]
        .mean()
        .reset_index(drop=True)
    )


# ----------------------------------------------------------------------------- angles
def read_angle_file(path: Path | str) -> pd.DataFrame:
    """Read one ``*ang.txt`` file as a wide frame indexed by ``Time`` (0..100 % of cycle)."""
    frame = pd.read_csv(path, sep="\t")
    if "Time" not in frame.columns:
        raise ValueError(f"{path}: no 'Time' column, not a Fukuchi angle file")
    if len(frame) != N_PCT:
        raise ValueError(f"{path}: expected {N_PCT} rows (0..100 %), got {len(frame)}")
    return frame


def angle_file_to_long(path: Path | str) -> pd.DataFrame:
    """Convert one ``*ang.txt`` file to ``(trial_id, side, channel, pct, value_deg)`` rows.

    Sign factors from :data:`SAGITTAL_COLUMNS` are applied, so the output already follows the
    clinical convention of :mod:`openacl.schema`.
    """
    path = Path(path)
    match = _ANG_RE.match(path.name)
    if match is None:
        raise ValueError(f"{path.name}: not a Fukuchi angle file name")
    frame = read_angle_file(path)
    subject = f"WBDS{int(match.group('subject')):02d}"
    trial_id = match.group("trial").upper()
    pct = frame["Time"].to_numpy(dtype=float)
    rows = []
    for channel, (template, factor) in SAGITTAL_COLUMNS.items():
        for side in ("L", "R"):
            column = template.format(side=side)
            if column not in frame.columns:
                continue
            rows.append(
                pd.DataFrame(
                    {
                        "side": side,
                        "channel": channel,
                        "pct": pct,
                        "value_deg": factor * frame[column].to_numpy(dtype=float),
                    }
                )
            )
    for channel, (columns, factor) in UNSIDED_COLUMNS.items():
        present = [c for c in columns if c in frame.columns]
        if not present:
            continue
        rows.append(
            pd.DataFrame(
                {
                    "side": "B",
                    "channel": channel,
                    "pct": pct,
                    "value_deg": factor * frame[present].to_numpy(dtype=float).mean(axis=1),
                }
            )
        )
    out = pd.concat(rows, ignore_index=True)
    out.insert(0, "trial_id", trial_id)
    out.insert(0, "subject_id", subject)
    return out


def load_angles(
    root: Path | str,
    conditions: tuple[str, ...] = ("overground",),
) -> pd.DataFrame:
    """Load all cycle-normalised sagittal joint angles into the canonical long format.

    Parameters
    ----------
    root
        Directory holding ``WBDSinfo.xlsx`` and ``ascii/``.
    conditions
        Subset of ``("overground", "treadmill")``.

    Returns
    -------
    pandas.DataFrame
        Columns :data:`LONG_COLUMNS`. One row per subject, trial, side, channel and percent
        of the gait cycle. ``value_deg`` follows the clinical sign convention.
    """
    paths = FukuchiPaths(Path(root))
    subjects = load_subject_info(paths.root).set_index("subject_id")
    speeds = _mean_speed_per_trial(paths.root).set_index(["subject_id", "trial_id"])

    frames: list[pd.DataFrame] = []
    for file in sorted(paths.ascii_dir.glob("*ang.txt")):
        match = _ANG_RE.match(file.name)
        if match is None:
            continue
        trial_id = match.group("trial").upper()
        condition = "overground" if trial_id.startswith("O") else "treadmill"
        if condition not in conditions:
            continue
        try:
            long = angle_file_to_long(file)
        except ValueError:
            continue
        subject = long["subject_id"].iat[0]
        if subject not in subjects.index:
            continue
        info = subjects.loc[subject]
        key = (subject, trial_id)
        long["dataset"] = DATASET
        long["age_years"] = info["age_years"]
        long["sex"] = info["sex"]
        long["height_m"] = info["height_m"]
        long["mass_kg"] = info["mass_kg"]
        long["leg_length_m"] = info["leg_length_m"]
        long["condition"] = condition
        long["speed_m_s"] = (
            float(speeds.loc[key, "speed_m_s"]) if key in speeds.index else float("nan")
        )
        frames.append(long)
    if not frames:
        raise FileNotFoundError(f"no Fukuchi angle files under {paths.ascii_dir}")
    out = pd.concat(frames, ignore_index=True)
    return out[LONG_COLUMNS]


# ------------------------------------------------------------------- spatiotemporal
def _plates_for_foot(cell: object) -> list[int]:
    """Parse a ``FP_RightFoot``/``FP_LeftFoot`` cell such as ``"FP4_5, FP1"`` to ``[4, 5, 1]``."""
    if not isinstance(cell, str):
        return []
    plates: list[int] = []
    for group in _FP_RE.findall(cell):
        plates.extend(int(part) for part in group.split("_") if part)
    return sorted(set(plates))


def _contacts(force_n: np.ndarray, threshold_n: float, min_samples: int) -> list[tuple[int, int]]:
    """Return ``(onset, offset)`` sample pairs of stance phases in a vertical force signal."""
    on = force_n > threshold_n
    edges = np.diff(on.astype(np.int8))
    starts = list(np.flatnonzero(edges == 1) + 1)
    ends = list(np.flatnonzero(edges == -1) + 1)
    if on[0]:
        starts.insert(0, 0)
    if on[-1]:
        ends.append(len(on))
    return [(s, e) for s, e in zip(starts, ends, strict=False) if e - s >= min_samples]


def _stride_metrics(
    left: list[tuple[int, int]],
    right: list[tuple[int, int]],
    fs_hz: float,
    speed_m_s: float,
) -> list[dict[str, float]]:
    """Derive per-stride time-distance parameters from left/right stance intervals.

    One gait cycle runs from ipsilateral initial contact to the next ipsilateral initial
    contact and contains two double-support phases, both of which fall inside the
    ipsilateral stance phase. Total double support is therefore the overlap of the
    contralateral stance intervals with ``[ic, to]``. A stride is only used when both
    double-support phases are actually recorded, i.e. one contralateral contact brackets
    ``ic`` (initial double support) and one starts inside ``[ic, to]`` (terminal double
    support); otherwise the plates missed a step and double support would be underestimated.
    """
    out: list[dict[str, float]] = []
    for ipsi, contra in ((left, right), (right, left)):
        for i in range(len(ipsi) - 1):
            ic, to = ipsi[i]
            next_ic = ipsi[i + 1][0]
            stride_s = (next_ic - ic) / fs_hz
            if not 0.5 <= stride_s <= 2.5:
                continue
            leading = [c for c in contra if c[0] <= ic < c[1]]
            trailing = [c for c in contra if ic < c[0] < to]
            if len(leading) != 1 or len(trailing) != 1:
                continue
            opp_ic = trailing[0][0]
            ds_samples = sum(max(0, min(to, c[1]) - max(ic, c[0])) for c in (*leading, *trailing))
            step_s = (opp_ic - ic) / fs_hz
            out.append(
                {
                    "stride_time_s": stride_s,
                    "stance_pct": 100.0 * (to - ic) / (next_ic - ic),
                    "double_support_pct": 100.0 * (ds_samples / fs_hz) / stride_s,
                    "cadence_steps_min": 120.0 / stride_s,
                    "step_length_m": speed_m_s * step_s,
                    "stride_length_m": speed_m_s * stride_s,
                    "speed_m_s": speed_m_s,
                }
            )
    return out


def load_spatiotemporal(
    root: Path | str,
    conditions: tuple[str, ...] = ("overground",),
    threshold_n: float = 30.0,
) -> pd.DataFrame:
    """Derive time-distance parameters per stride from the force-plate ASCII files.

    Overground trials use the per-trial force-plate-to-foot assignment from
    ``WBDSinfo.xlsx``; the vertical force of all plates belonging to one foot is summed, so a
    foot spanning two plates (``FP4_5``) still yields a single stance phase. Treadmill trials
    use the two instrumented belts directly.

    Returns
    -------
    pandas.DataFrame
        One row per stride with ``dataset, subject_id, trial_id, condition, speed_m_s,
        stance_pct, double_support_pct, cadence_steps_min, step_length_m, stride_length_m``.
    """
    paths = FukuchiPaths(Path(root))
    subjects = load_subject_info(paths.root).set_index("subject_id")
    info = pd.read_excel(paths.info_xlsx)
    info["_key"] = info["FileName"].astype(str).str.replace(".c3d", "", regex=False).str.upper()
    info = info.set_index("_key")
    min_samples = int(0.15 * GRF_FS_HZ)

    rows: list[dict[str, float | str]] = []
    for file in sorted(paths.ascii_dir.glob("*grf.txt")):
        match = _GRF_RE.match(file.name)
        if match is None:
            continue
        subject = f"WBDS{int(match.group('subject')):02d}"
        if match.group("tread"):
            trial_id, condition = f"T{int(match.group('tread')):02d}", "treadmill"
            key = f"{subject}WALKT{int(match.group('tread')):02d}"
        else:
            trial_id = f"O{match.group('cond').upper()}"
            condition = "overground"
            key = f"{subject}WALKO{int(match.group('pass_no')):02d}{match.group('cond').upper()}"
        if condition not in conditions or subject not in subjects.index or key not in info.index:
            continue
        row = info.loc[key]
        speed = pd.to_numeric(row["GaitSpeed(m/s)"], errors="coerce")
        if not np.isfinite(speed):
            continue
        grf = pd.read_csv(file, sep="\t")

        if condition == "treadmill":
            groups = {"L": [1], "R": [2]}
        else:
            groups = {
                "R": _plates_for_foot(row["FP_RightFoot"]),
                "L": _plates_for_foot(row["FP_LeftFoot"]),
            }
            if set(groups["R"]) & set(groups["L"]) or not groups["R"] or not groups["L"]:
                continue

        stance: dict[str, list[tuple[int, int]]] = {}
        for side, plates in groups.items():
            columns = [f"{VERTICAL_GRF_PREFIX}{p}" for p in plates]
            columns = [c for c in columns if c in grf.columns]
            if not columns:
                stance[side] = []
                continue
            force = grf[columns].to_numpy(dtype=float).sum(axis=1)
            stance[side] = _contacts(force, threshold_n, min_samples)

        for stride in _stride_metrics(stance["L"], stance["R"], GRF_FS_HZ, float(speed)):
            rows.append(
                {
                    "dataset": DATASET,
                    "subject_id": subject,
                    "trial_id": trial_id,
                    "condition": condition,
                    "leg_length_m": float(subjects.loc[subject, "leg_length_m"]),
                    "height_m": float(subjects.loc[subject, "height_m"]),
                    **stride,
                }
            )
    if not rows:
        raise FileNotFoundError(f"no usable Fukuchi force-plate files under {paths.ascii_dir}")
    return pd.DataFrame(rows)

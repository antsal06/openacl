"""Loader for the Van Criekinge et al. (2023) able-bodied gait dataset (post-processed Excel).

Source
------
Van Criekinge T, Saeys W, Truijen S, et al. *A full-body motion capture gait dataset of 138
able-bodied adults across the life span and 50 stroke survivors.* Sci Data 10:852 (2023).
figshare collection doi:10.6084/m9.figshare.c.6503791 -- the post-processed Excel file used
here (article 24192489) is released under **CC0 1.0**.

What this loader reads
----------------------
``MAT_normalizedData_AbleBodiedAdults_v06-03-23.xlsx``: one worksheet per subject
(``Sub01``..``Sub138``), 1001 rows spanning one gait cycle, columns ``AnkleAngles``,
``KneeAngles``, ``HipAngles``, ``PelvisAngles`` (Plug-in-Gait, sagittal plane, degrees) plus
moments, powers, EMG and GRF which we ignore.

Known limitations
-----------------
- The curves are **already averaged over strides and over the left and right side**, so this
  dataset contributes one curve per subject and carries no side information.
- The Excel export contains **no walking speed, age, sex, height or mass**; those live only
  in the 6.2 GB MAT structure. Froude scaling is therefore impossible and the data cannot
  enter the speed-classified norm bands. All participants walked barefoot at their
  *preferred* speed, so the pooled curve is used as an independent cross-check of the
  Fukuchi comfortable-speed band.
- Plug-in-Gait differs from the model used by Fukuchi; systematic offsets of a few degrees
  (most notably at the ankle) are expected between the two datasets.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from openacl.core.normband import N_POINTS

DATASET = "vancriekinge2023"
EXCEL_NAME = "MAT_normalizedData_AbleBodiedAdults_v06-03-23.xlsx"
N_RAW_POINTS = 1001

#: canonical channel -> (worksheet column, sign factor towards the clinical convention)
SAGITTAL_COLUMNS: dict[str, tuple[str, float]] = {
    "hip_flexion_deg": ("HipAngles", +1.0),
    "knee_flexion_deg": ("KneeAngles", +1.0),
    "ankle_dorsiflexion_deg": ("AnkleAngles", +1.0),
    "pelvis_tilt_deg": ("PelvisAngles", +1.0),
}


def resample_to_pct(values: np.ndarray, n_points: int = N_POINTS) -> np.ndarray:
    """Linearly resample a cycle-normalised curve onto ``0..100 %`` with ``n_points`` samples."""
    values = np.asarray(values, dtype=float)
    source = np.linspace(0.0, 100.0, values.size)
    target = np.linspace(0.0, 100.0, n_points)
    return np.interp(target, source, values)


def load_angles(root: Path | str) -> pd.DataFrame:
    """Load the sagittal joint angles of all able-bodied subjects into the long format.

    Returns
    -------
    pandas.DataFrame
        Same columns as :data:`openacl.norm.fukuchi.LONG_COLUMNS`. ``side`` is ``"B"``
        (already pooled), ``speed_m_s`` is ``NaN`` and demographics are ``NaN``.
    """
    path = Path(root)
    if path.is_dir():
        path = path / EXCEL_NAME
    book = pd.ExcelFile(path)
    sheets = [s for s in book.sheet_names if s.lower().startswith("sub")]
    frames: list[pd.DataFrame] = []
    for sheet in sheets:
        wide = book.parse(sheet)
        for channel, (column, factor) in SAGITTAL_COLUMNS.items():
            if column not in wide.columns:
                continue
            raw = pd.to_numeric(wide[column], errors="coerce").to_numpy(dtype=float)
            if np.all(np.isnan(raw)):
                continue
            frames.append(
                pd.DataFrame(
                    {
                        "dataset": DATASET,
                        "subject_id": sheet,
                        "age_years": np.nan,
                        "sex": "U",
                        "height_m": np.nan,
                        "mass_kg": np.nan,
                        "leg_length_m": np.nan,
                        "trial_id": "preferred",
                        "speed_m_s": np.nan,
                        "condition": "overground",
                        "side": "B",
                        "channel": channel,
                        "pct": np.linspace(0.0, 100.0, N_POINTS),
                        "value_deg": factor * resample_to_pct(raw),
                    }
                )
            )
    if not frames:
        raise FileNotFoundError(f"no usable subject sheets in {path}")
    return pd.concat(frames, ignore_index=True)

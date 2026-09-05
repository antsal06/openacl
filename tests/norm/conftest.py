"""Synthetic fixtures in the Fukuchi ASCII layout; no network access anywhere in these tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

N_PCT = 101

ANGLE_COLUMNS = [
    f"{side}{joint}Angle{axis}"
    for side in ("R", "L")
    for joint in ("Pelvis", "Hip", "Knee", "Ankle")
    for axis in ("X", "Y", "Z")
]


def _synthetic_cycle(kind: str, scale: float) -> np.ndarray:
    """Crude but realistically shaped sagittal curve over 0..100 % of the gait cycle."""
    pct = np.linspace(0.0, 100.0, N_PCT)
    phase = 2 * np.pi * pct / 100.0
    if kind == "knee":
        # loading response bump plus the large swing peak
        return scale * (
            0.25 * np.exp(-(((pct - 15) / 8) ** 2)) + 1.0 * np.exp(-(((pct - 73) / 12) ** 2))
        )
    if kind == "hip":
        return scale * np.cos(phase) * 0.5 + scale * 0.25
    if kind == "ankle":
        return scale * (0.6 * np.sin(phase) - 1.0 * np.exp(-(((pct - 62) / 6) ** 2)))
    return scale * 0.1 * np.sin(phase)


def write_angle_file(path: Path, knee_peak_deg: float, hip_scale: float = 60.0) -> Path:
    """Write one ``*ang.txt`` file with the real column layout and tab separator."""
    frame = pd.DataFrame({"Time": np.arange(N_PCT)})
    for column in ANGLE_COLUMNS:
        frame[column] = 0.0
    for side in ("R", "L"):
        frame[f"{side}KneeAngleZ"] = _synthetic_cycle("knee", knee_peak_deg)
        frame[f"{side}HipAngleZ"] = _synthetic_cycle("hip", hip_scale)
        frame[f"{side}AnkleAngleZ"] = _synthetic_cycle("ankle", 14.0)
        frame[f"{side}PelvisAngleZ"] = 12.0 + _synthetic_cycle("pelvis", 4.0)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, sep="\t", index=False)
    return path


def write_info_xlsx(path: Path, subjects: list[dict]) -> Path:
    """Write a minimal ``WBDSinfo.xlsx`` with one row per subject and per trial."""
    rows = []
    for subject in subjects:
        number = subject["number"]
        base = {
            "Subject": number,
            "AgeGroup": subject.get("age_group", "Young"),
            "Age": subject.get("age_years", 27),
            "Height": subject["height_cm"],
            "Mass": subject.get("mass_kg", 70.0),
            "Gender": subject.get("sex", "M"),
            "Dominance": "R",
            "LegLength": subject["leg_length_m"],
        }
        for condition, speed in subject["overground"].items():
            for pass_no in (1, 2):
                rows.append(
                    {
                        **base,
                        "FileName": f"WBDS{number:02d}walkO{pass_no:02d}{condition}.c3d",
                        "GaitSpeed(m/s)": speed,
                        "FP_RightFoot": "FP4, FP1",
                        "FP_LeftFoot": "FP3, FP2",
                    }
                )
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_excel(path, index=False)
    return path


@pytest.fixture
def fukuchi_root(tmp_path: Path) -> Path:
    """A miniature Fukuchi dataset: 6 subjects x 3 overground speed conditions."""
    root = tmp_path / "fukuchi2018"
    subjects = []
    for i in range(1, 7):
        height_cm = 160.0 + 5.0 * i
        subjects.append(
            {
                "number": i,
                "height_cm": height_cm,
                "leg_length_m": 0.52 * height_cm / 100.0,
                "sex": "M" if i % 2 else "F",
                "age_years": 20 + i,
                "overground": {"S": 0.80 + 0.02 * i, "C": 1.20 + 0.02 * i, "F": 1.60 + 0.02 * i},
            }
        )
    write_info_xlsx(root / "WBDSinfo.xlsx", subjects)
    for subject in subjects:
        for condition, peak in (("S", 56.0), ("C", 61.0), ("F", 64.0)):
            write_angle_file(
                root / "ascii" / f"WBDS{subject['number']:02d}walkO{condition}ang.txt",
                knee_peak_deg=peak + subject["number"] * 0.5,
            )
    return root

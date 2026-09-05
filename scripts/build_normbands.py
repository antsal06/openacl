#!/usr/bin/env python3
"""Build ``src/openacl/norm/data/normbands_v1.parquet`` from the downloaded reference data.

End-to-end reproducible::

    python scripts/download_normdata.py --dataset fukuchi2018
    python scripts/download_normdata.py --dataset vancriekinge2023
    python scripts/build_normbands.py

Plausibility gates (healthy adults, sagittal plane) are checked before anything is written:
peak knee flexion in swing 55-70 deg, stance 56-64 % of the cycle, cadence 90-135 steps/min.
A failure means a sign or a normalisation is wrong, so the file is not saved.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from openacl.norm import bands as nb
from openacl.norm import fukuchi, vancriekinge

SCRIPT_VERSION = "1.0.0"
DEFAULT_DATA_ROOT = REPO_ROOT / "data" / "norm"

PLAUSIBILITY = {
    "peak_knee_flexion_deg": (55.0, 70.0),
    "stance_pct": (56.0, 64.0),
    "cadence_steps_min": (90.0, 135.0),
    "double_support_pct": (12.0, 30.0),
}

DATASET_INFO = {
    "fukuchi2018": {
        "key": "fukuchi2018",
        "citation": (
            "Fukuchi CA, Fukuchi RK, Duarte M (2018). A public data set of overground and "
            "treadmill walking kinematics and kinetics of healthy individuals. PeerJ 6:e4640."
        ),
        "doi": "10.6084/m9.figshare.5722711",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "role": "speed-classified angle bands and time-distance parameters (overground)",
    },
    "vancriekinge2023": {
        "key": "vancriekinge2023",
        "citation": (
            "Van Criekinge T, Saeys W, Truijen S, et al. (2023). A full-body motion capture gait "
            "dataset of 138 able-bodied adults across the life span and 50 stroke survivors. "
            "Sci Data 10:852."
        ),
        "doi": "10.6084/m9.figshare.c.6503791",
        "license": "CC0 1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "role": (
            "independent cross-check at preferred speed; no speed/anthropometrics in the "
            "public Excel export, therefore no Froude class"
        ),
    },
}


def build_fukuchi(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, tuple[float, float]]:
    """Return (angle bands, scalar bands, Froude tercile edges) from the Fukuchi data."""
    angles = fukuchi.load_angles(root, conditions=("overground",))
    angles = nb.add_froude(angles)
    labels, edges = nb.assign_speed_class(angles["froude"].to_numpy(dtype=float))
    angles["speed_class"] = labels

    strides = fukuchi.load_spatiotemporal(root, conditions=("overground",))
    strides = nb.add_froude(strides)
    stride_labels, _ = nb.assign_speed_class(strides["froude"].to_numpy(dtype=float), edges=edges)
    strides["speed_class"] = stride_labels

    angle_bands = nb.build_angle_bands(angles, DATASET_INFO["fukuchi2018"]["citation"])
    scalar_bands = nb.build_scalar_bands(strides, fukuchi.DATASET)
    return angle_bands, scalar_bands, edges


def build_vancriekinge(root: Path) -> pd.DataFrame:
    """Return the pooled preferred-speed cross-check band, or an empty frame if absent."""
    if not root.exists():
        return pd.DataFrame(columns=nb.BAND_COLUMNS)
    angles = vancriekinge.load_angles(root)
    angles["speed_class"] = "preferred"
    return nb.build_angle_bands(angles, DATASET_INFO["vancriekinge2023"]["citation"])


def summarise(bands: pd.DataFrame) -> pd.DataFrame:
    """One row per channel and speed class with n and the peak of the mean curve."""
    rows = []
    for (dataset, kind, channel, speed_class), part in bands.groupby(
        ["dataset", "kind", "channel", "speed_class"]
    ):
        mean = part["mean"].to_numpy(dtype=float)
        rows.append(
            {
                "dataset": dataset,
                "channel": channel,
                "class": speed_class,
                "n_subj": int(part["n_subjects"].max()),
                "n_curves": int(part["n_curves"].max()),
                "peak_mean": float(np.nanmax(mean)) if kind == "angle_curve" else float(mean[0]),
                "min_mean": float(np.nanmin(mean)) if kind == "angle_curve" else float(mean[0]),
                "sd_at_peak": float(part["sd"].to_numpy()[int(np.nanargmax(mean))])
                if kind == "angle_curve"
                else float(part["sd"].iat[0]),
                "unit": part["unit"].iat[0],
            }
        )
    return pd.DataFrame(rows).sort_values(["dataset", "channel", "class"]).reset_index(drop=True)


def check_plausibility(bands: pd.DataFrame) -> list[str]:
    """Return a list of human readable violations; empty means everything is in range."""
    problems: list[str] = []
    knee = bands[(bands["kind"] == "angle_curve") & (bands["channel"] == "knee_flexion_deg")]
    for (dataset, speed_class), part in knee.groupby(["dataset", "speed_class"]):
        # peak flexion in swing, i.e. after 50 % of the cycle
        swing = part[part["pct"] >= 50.0]["mean"].to_numpy(dtype=float)
        peak = float(np.nanmax(swing))
        lo, hi = PLAUSIBILITY["peak_knee_flexion_deg"]
        if not lo <= peak <= hi:
            problems.append(
                f"{dataset}/{speed_class}: peak knee flexion in swing {peak:.1f} deg "
                f"outside [{lo}, {hi}]"
            )
    scalars = bands[bands["kind"] == "scalar"]
    for parameter, (lo, hi) in PLAUSIBILITY.items():
        if parameter == "peak_knee_flexion_deg":
            continue
        for _, row in scalars[scalars["channel"] == parameter].iterrows():
            if not lo <= row["mean"] <= hi:
                problems.append(
                    f"{row['dataset']}/{row['speed_class']}: {parameter} {row['mean']:.1f} "
                    f"outside [{lo}, {hi}]"
                )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--out-dir", type=Path, default=None, help="default: norm/data in package")
    parser.add_argument(
        "--force", action="store_true", help="save even if a plausibility check fails"
    )
    parser.add_argument(
        "--plot", type=Path, default=REPO_ROOT / "docs" / "img" / "normbands_v1.png"
    )
    args = parser.parse_args(argv)

    print("== Fukuchi 2018 (overground)")
    angle_bands, scalar_bands, edges = build_fukuchi(args.data_root / "fukuchi2018")
    print(f"   Froude tercile edges: {edges[0]:.4f} / {edges[1]:.4f}")

    print("== Van Criekinge 2023 (preferred speed, cross-check)")
    cross_bands = build_vancriekinge(args.data_root / "vancriekinge2023")
    if cross_bands.empty:
        print("   not downloaded, skipped")

    bands = pd.concat([angle_bands, scalar_bands, cross_bands], ignore_index=True)

    print("\n== summary")
    print(summarise(bands).to_string(index=False, float_format=lambda v: f"{v:8.2f}"))

    problems = check_plausibility(bands)
    print("\n== plausibility")
    if problems:
        for p in problems:
            print(f"   FAIL {p}")
        if not args.force:
            print("\nnothing written; fix the sign or normalisation first (or pass --force)")
            return 1
    else:
        print("   all checks passed")

    froude_edges = {"fukuchi2018": edges}
    datasets = [DATASET_INFO["fukuchi2018"]]
    if not cross_bands.empty:
        datasets.append(DATASET_INFO["vancriekinge2023"])
    metadata = nb.normband_metadata(
        bands,
        datasets=datasets,
        froude_edges=froude_edges,
        script_version=SCRIPT_VERSION,
        extra={
            "condition": "overground walking only",
            "plausibility_ranges": PLAUSIBILITY,
            "known_limitations": [
                "marker-based optical motion capture; smartphone video measures differently",
                (
                    "Van Criekinge curves are already pooled over sides and strides and carry "
                    "no walking speed, so they are stored as a separate 'preferred' class"
                ),
                "time-distance parameters come from force-plate events of overground passes",
            ],
        },
    )
    path = nb.save_normbands(bands, metadata, args.out_dir)
    size_kb = path.stat().st_size / 1024
    print(f"\nwrote {path} ({size_kb:.0f} kB) and {path.with_name(nb.JSON_NAME).name}")

    if args.plot is not None:
        from plot_normbands import plot_bands

        args.plot.parent.mkdir(parents=True, exist_ok=True)
        plot_bands(bands, args.plot)
        print(f"wrote {args.plot}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())

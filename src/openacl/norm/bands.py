"""Speed-classified norm bands for sagittal joint angles and time-distance parameters.

Speed classification
--------------------
Walking speed is made dimensionless with the Froude number after Hof,
``Fr = v^2 / (g * L_leg)``, so that people of different body size are compared at
*dynamically similar* speeds. Where a measured leg length is missing, ``L_leg = 0.53 * height``
is used (see :func:`leg_length_m`).

Curves are grouped into three classes -- ``slow`` / ``comfortable`` / ``fast`` -- by the
**terciles of the Froude number** of the pooled reference curves. Rationale for terciles over
a regression on Froude: with 42 reference subjects a regression would have to extrapolate at
the edges, its residual scatter is what the interpretation layer needs anyway (deviation
relative to MDC), and three discrete bands are what a clinician actually reads off a report.
The tercile edges are stored in the metadata JSON, so a new measurement can be assigned to a
class by its own Froude number. The class boundaries can be replaced by a regression later
without touching the consumers, because they only see :class:`NormBand`.

Left and right are pooled: in healthy adults the sagittal side difference is far below the
between-subject scatter, and pooling doubles the number of curves per band.

Storage
-------
``normbands_v1.parquet`` (long format, one row per channel/class/percent) plus
``normbands_v1.json`` with data sets, licenses, processing date, script version and n.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from openacl.core.normband import N_POINTS, NormBand

__all__ = [
    "N_POINTS",
    "SPEED_CLASSES",
    "BandKey",
    "NormBand",
    "add_froude",
    "assign_speed_class",
    "build_angle_bands",
    "build_scalar_bands",
    "froude",
    "leg_length_m",
    "load_normbands",
    "normband_metadata",
    "save_normbands",
]

G_M_S2 = 9.80665
SPEED_CLASSES: tuple[str, ...] = ("slow", "comfortable", "fast")
LEG_LENGTH_HEIGHT_RATIO = 0.53
"""Fallback leg length as a fraction of body height (Winter's anthropometric tables)."""

DATA_DIR = Path(__file__).resolve().parent / "data"
PARQUET_NAME = "normbands_v1.parquet"
JSON_NAME = "normbands_v1.json"

BAND_COLUMNS = [
    "kind",
    "dataset",
    "channel",
    "speed_class",
    "pct",
    "mean",
    "sd",
    "p5",
    "p95",
    "n_subjects",
    "n_curves",
    "unit",
]

#: scalar time-distance parameters kept in the norm band file, with their unit
SCALAR_PARAMETERS: dict[str, str] = {
    "stance_pct": "pct",
    "double_support_pct": "pct",
    "cadence_steps_min": "steps_min",
    "step_length_m": "m",
    "stride_length_m": "m",
    "speed_m_s": "m_s",
}


@dataclass(frozen=True)
class BandKey:
    """Identifies one band: canonical channel plus speed class."""

    channel: str
    speed_class: str

    def __str__(self) -> str:
        return f"{self.channel}@{self.speed_class}"


# ------------------------------------------------------------------ speed normalisation
def leg_length_m(
    leg_length_m_measured: float | np.ndarray, height_m: float | np.ndarray
) -> np.ndarray:
    """Return leg length, falling back to ``0.53 * height`` where the measurement is missing."""
    measured = np.asarray(leg_length_m_measured, dtype=float)
    height = np.asarray(height_m, dtype=float)
    return np.where(np.isfinite(measured), measured, LEG_LENGTH_HEIGHT_RATIO * height)


def froude(speed_m_s: float | np.ndarray, leg_length: float | np.ndarray) -> np.ndarray:
    """Dimensionless Froude number ``Fr = v^2 / (g * L_leg)`` (Hof 1996).

    ``Fr`` is ``NaN`` where speed or leg length is missing or non-positive.
    """
    speed = np.asarray(speed_m_s, dtype=float)
    leg = np.asarray(leg_length, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = speed**2 / (G_M_S2 * leg)
    return np.where(np.isfinite(out) & (leg > 0) & (speed > 0), out, np.nan)


def add_froude(frame: pd.DataFrame) -> pd.DataFrame:
    """Add a ``froude`` column derived from ``speed_m_s``, ``leg_length_m`` and ``height_m``."""
    out = frame.copy()
    legs = leg_length_m(out.get("leg_length_m", np.nan), out.get("height_m", np.nan))
    out["froude"] = froude(out["speed_m_s"].to_numpy(dtype=float), legs)
    return out


def assign_speed_class(
    froude_values: np.ndarray, edges: tuple[float, float] | None = None
) -> tuple[np.ndarray, tuple[float, float]]:
    """Bin Froude numbers into ``slow``/``comfortable``/``fast``.

    Parameters
    ----------
    froude_values
        Froude numbers; ``NaN`` maps to ``None``.
    edges
        Lower and upper cut. If omitted, the 33.3 and 66.7 percentiles of the finite values
        are used (tercile split).

    Returns
    -------
    tuple
        Array of class labels (``object`` dtype) and the edges actually used.
    """
    values = np.asarray(froude_values, dtype=float)
    finite = values[np.isfinite(values)]
    if edges is None:
        if finite.size < 3:
            raise ValueError("need at least three finite Froude numbers for a tercile split")
        edges = (float(np.quantile(finite, 1 / 3)), float(np.quantile(finite, 2 / 3)))
    lo, hi = edges
    labels = np.full(values.shape, None, dtype=object)
    labels[np.isfinite(values) & (values < lo)] = "slow"
    labels[np.isfinite(values) & (values >= lo) & (values < hi)] = "comfortable"
    labels[np.isfinite(values) & (values >= hi)] = "fast"
    return labels, (lo, hi)


# ------------------------------------------------------------------------- band building
def _pivot_curves(long: pd.DataFrame) -> tuple[np.ndarray, pd.DataFrame]:
    """Turn long-format rows into a ``(n_curves, 101)`` stack plus its curve index."""
    wide = long.pivot_table(
        index=["dataset", "subject_id", "trial_id", "side"],
        columns="pct",
        values="value_deg",
        aggfunc="mean",
    )
    grid = np.linspace(0.0, 100.0, N_POINTS)
    if list(wide.columns) != list(grid):
        resampled = np.vstack(
            [np.interp(grid, np.asarray(wide.columns, dtype=float), row) for row in wide.to_numpy()]
        )
    else:
        resampled = wide.to_numpy(dtype=float)
    return resampled, wide.index.to_frame(index=False)


def build_angle_bands(long: pd.DataFrame, source: str) -> pd.DataFrame:
    """Aggregate long-format angle curves into per-channel, per-class band statistics.

    Parameters
    ----------
    long
        Long-format frame with a ``speed_class`` column (see :func:`assign_speed_class`).
    source
        Citation string stored with every band.

    Returns
    -------
    pandas.DataFrame
        Rows in :data:`BAND_COLUMNS` with ``kind == "angle_curve"``.
    """
    rows: list[pd.DataFrame] = []
    for (channel, speed_class), part in long.groupby(["channel", "speed_class"], dropna=True):
        curves, index = _pivot_curves(part)
        if curves.shape[0] < 2:
            continue
        with np.errstate(invalid="ignore"):
            mean = np.nanmean(curves, axis=0)
            sd = np.nanstd(curves, axis=0, ddof=1)
            p5 = np.nanpercentile(curves, 5, axis=0)
            p95 = np.nanpercentile(curves, 95, axis=0)
        rows.append(
            pd.DataFrame(
                {
                    "kind": "angle_curve",
                    "dataset": part["dataset"].iat[0],
                    "channel": channel,
                    "speed_class": speed_class,
                    "pct": np.linspace(0.0, 100.0, N_POINTS),
                    "mean": mean,
                    "sd": sd,
                    "p5": p5,
                    "p95": p95,
                    "n_subjects": index["subject_id"].nunique(),
                    "n_curves": curves.shape[0],
                    "unit": "deg",
                }
            )
        )
    if not rows:
        raise ValueError("no angle bands could be built; check the speed_class column")
    out = pd.concat(rows, ignore_index=True)
    out.attrs["source"] = source
    return out[BAND_COLUMNS]


def build_scalar_bands(strides: pd.DataFrame, dataset: str) -> pd.DataFrame:
    """Aggregate per-stride time-distance parameters into per-class mean/SD rows.

    The mean is taken over subject means, so a subject with many recorded strides does not
    dominate; ``n_subjects`` is the number of subjects and ``n_curves`` the number of strides.
    """
    rows: list[dict[str, object]] = []
    for (parameter, speed_class), part in (
        strides.melt(
            id_vars=["subject_id", "speed_class"],
            value_vars=[p for p in SCALAR_PARAMETERS if p in strides.columns],
            var_name="channel",
            value_name="value",
        )
        .dropna(subset=["value", "speed_class"])
        .groupby(["channel", "speed_class"])
    ):
        per_subject = part.groupby("subject_id")["value"].mean()
        if per_subject.size < 2:
            continue
        rows.append(
            {
                "kind": "scalar",
                "dataset": dataset,
                "channel": parameter,
                "speed_class": speed_class,
                "pct": np.nan,
                "mean": float(per_subject.mean()),
                "sd": float(per_subject.std(ddof=1)),
                "p5": float(np.percentile(per_subject, 5)),
                "p95": float(np.percentile(per_subject, 95)),
                "n_subjects": int(per_subject.size),
                "n_curves": int(part.shape[0]),
                "unit": SCALAR_PARAMETERS[parameter],
            }
        )
    if not rows:
        raise ValueError("no scalar bands could be built; check the speed_class column")
    return pd.DataFrame(rows)[BAND_COLUMNS]


# ------------------------------------------------------------------------------ storage
def normband_metadata(
    bands: pd.DataFrame,
    datasets: list[dict[str, str]],
    froude_edges: dict[str, tuple[float, float]],
    script_version: str,
    extra: dict | None = None,
) -> dict:
    """Assemble the sidecar metadata written next to the parquet file."""
    counts = (
        bands.groupby(["dataset", "kind", "channel", "speed_class"])[["n_subjects", "n_curves"]]
        .max()
        .reset_index()
    )
    return {
        "version": "v1",
        "script_version": script_version,
        "processed_utc": pd.Timestamp.now("UTC").isoformat(timespec="seconds"),
        "n_points": N_POINTS,
        "speed_classes": list(SPEED_CLASSES),
        "froude_edges": {k: list(v) for k, v in froude_edges.items()},
        "froude_definition": "Fr = v^2 / (g * L_leg), g = 9.80665 m/s^2",
        "leg_length_fallback": f"L_leg = {LEG_LENGTH_HEIGHT_RATIO} * height_m",
        "sides": "left and right pooled",
        "datasets": datasets,
        "counts": counts.to_dict(orient="records"),
        **(extra or {}),
    }


def save_normbands(bands: pd.DataFrame, metadata: dict, data_dir: Path | None = None) -> Path:
    """Write ``normbands_v1.parquet`` and ``normbands_v1.json``; returns the parquet path."""
    directory = Path(data_dir) if data_dir is not None else DATA_DIR
    directory.mkdir(parents=True, exist_ok=True)
    parquet_path = directory / PARQUET_NAME
    bands[BAND_COLUMNS].to_parquet(parquet_path, index=False, compression="zstd")
    (directory / JSON_NAME).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return parquet_path


def read_normband_table(data_dir: Path | None = None) -> pd.DataFrame:
    """Return the raw long-format band table shipped with the package."""
    directory = Path(data_dir) if data_dir is not None else DATA_DIR
    return pd.read_parquet(directory / PARQUET_NAME)


def read_normband_metadata(data_dir: Path | None = None) -> dict:
    """Return the metadata sidecar shipped with the package."""
    directory = Path(data_dir) if data_dir is not None else DATA_DIR
    return json.loads((directory / JSON_NAME).read_text(encoding="utf-8"))


def load_normbands(
    dataset: str | None = "fukuchi2018",
    kind: str = "angle_curve",
    data_dir: Path | None = None,
) -> dict[str, NormBand]:
    """Load the shipped norm bands as ``{"<channel>@<speed_class>": NormBand}``.

    Parameters
    ----------
    dataset
        Restrict to one reference data set; ``None`` returns every stored band. The default
        ``"fukuchi2018"`` is the only speed-classified source in ``v1``.
    kind
        ``"angle_curve"`` for the 101-point curves, ``"scalar"`` for the time-distance
        parameters (whose ``NormBand.mean``/``sd`` then have length 1).
    data_dir
        Override the packaged ``norm/data`` directory (used by tests).

    Returns
    -------
    dict[str, NormBand]
    """
    table = read_normband_table(data_dir)
    meta = read_normband_metadata(data_dir)
    sources = {d["key"]: d["citation"] for d in meta.get("datasets", [])}
    table = table[table["kind"] == kind]
    if dataset is not None:
        table = table[table["dataset"] == dataset]

    bands: dict[str, NormBand] = {}
    for (dataset_key, channel, speed_class), part in table.groupby(
        ["dataset", "channel", "speed_class"]
    ):
        part = part.sort_values("pct", na_position="first")
        bands[str(BandKey(channel, speed_class))] = NormBand(
            mean=part["mean"].to_numpy(dtype=float),
            sd=part["sd"].to_numpy(dtype=float),
            n=int(part["n_subjects"].max()),
            source=sources.get(dataset_key, dataset_key),
            unit=str(part["unit"].iat[0]),
            meta={
                "dataset": dataset_key,
                "channel": channel,
                "speed_class": speed_class,
                "n_curves": int(part["n_curves"].max()),
                "p5": part["p5"].to_numpy(dtype=float).tolist(),
                "p95": part["p95"].to_numpy(dtype=float).tolist(),
                "froude_edges": meta.get("froude_edges", {}).get(dataset_key),
            },
        )
    return bands

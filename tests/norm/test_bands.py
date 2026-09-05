"""Froude scaling, band aggregation and the packaged ``load_normbands()`` accessor."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from openacl.core.normband import N_POINTS, NormBand
from openacl.norm import bands as nb
from openacl.norm import fukuchi
from openacl.schema import ANGLE_CHANNELS

SIDED_CHANNELS = ("hip_flexion_deg", "knee_flexion_deg", "ankle_dorsiflexion_deg")


# ------------------------------------------------------------------------------- Froude
def test_froude_matches_the_definition() -> None:
    # v = 1.4 m/s, L = 0.9 m -> 1.96 / (9.80665 * 0.9)
    assert nb.froude(1.4, 0.9) == pytest.approx(1.4**2 / (nb.G_M_S2 * 0.9))


def test_froude_is_dimensionless_and_size_invariant() -> None:
    """Dynamically similar walkers have the same Froude number (Hof scaling)."""
    small = nb.froude(1.0, 0.80)
    large = nb.froude(1.0 * np.sqrt(1.00 / 0.80), 1.00)
    assert small == pytest.approx(large)


def test_froude_is_nan_for_missing_or_invalid_input() -> None:
    assert np.isnan(nb.froude(np.nan, 0.9))
    assert np.isnan(nb.froude(1.2, np.nan))
    assert np.isnan(nb.froude(1.2, 0.0))
    assert np.isnan(nb.froude(0.0, 0.9))


def test_leg_length_falls_back_to_height_fraction() -> None:
    assert nb.leg_length_m(0.91, 1.80) == pytest.approx(0.91)
    assert nb.leg_length_m(np.nan, 1.80) == pytest.approx(0.53 * 1.80)


def test_assign_speed_class_terciles() -> None:
    values = np.linspace(0.05, 0.35, 30)
    labels, edges = nb.assign_speed_class(values)
    assert edges[0] < edges[1]
    counts = pd.Series(labels).value_counts()
    assert set(counts.index) == set(nb.SPEED_CLASSES)
    assert counts.max() - counts.min() <= 1


def test_assign_speed_class_honours_given_edges_and_nan() -> None:
    values = np.array([0.05, 0.15, 0.30, np.nan])
    labels, edges = nb.assign_speed_class(values, edges=(0.10, 0.25))
    assert edges == (0.10, 0.25)
    assert labels.tolist() == ["slow", "comfortable", "fast", None]


def test_add_froude_uses_the_height_fallback() -> None:
    frame = pd.DataFrame(
        {"speed_m_s": [1.2, 1.2], "leg_length_m": [0.90, np.nan], "height_m": [1.75, 1.75]}
    )
    out = nb.add_froude(frame)
    assert out["froude"].iat[0] == pytest.approx(nb.froude(1.2, 0.90))
    assert out["froude"].iat[1] == pytest.approx(nb.froude(1.2, 0.53 * 1.75))


# ------------------------------------------------------------------------ band building
def _build_from_fixture(root: Path) -> tuple[pd.DataFrame, tuple[float, float]]:
    long = nb.add_froude(fukuchi.load_angles(root, conditions=("overground",)))
    labels, edges = nb.assign_speed_class(long["froude"].to_numpy(dtype=float))
    long["speed_class"] = labels
    return nb.build_angle_bands(long, source="test"), edges


def test_build_angle_bands_shapes(fukuchi_root: Path) -> None:
    bands, _ = _build_from_fixture(fukuchi_root)
    assert list(bands.columns) == nb.BAND_COLUMNS
    for (channel, speed_class), part in bands.groupby(["channel", "speed_class"]):
        assert len(part) == N_POINTS, f"{channel}/{speed_class} is not 101 points"
        assert part["pct"].min() == 0.0
        assert part["pct"].max() == 100.0
        assert (part["sd"] >= 0).all()
        assert (part["p5"] <= part["p95"]).all()
    assert set(bands["speed_class"]) == set(nb.SPEED_CLASSES)
    assert set(bands["channel"]) <= set(ANGLE_CHANNELS)


def test_build_angle_bands_pools_left_and_right(fukuchi_root: Path) -> None:
    bands, _ = _build_from_fixture(fukuchi_root)
    knee = bands[(bands["channel"] == "knee_flexion_deg") & (bands["speed_class"] == "comfortable")]
    # each subject contributes a left and a right curve
    assert knee["n_curves"].max() == 2 * knee["n_subjects"].max()


def test_build_angle_bands_peak_is_plausible(fukuchi_root: Path) -> None:
    bands, _ = _build_from_fixture(fukuchi_root)
    knee = bands[bands["channel"] == "knee_flexion_deg"]
    for _, part in knee.groupby("speed_class"):
        swing = part[part["pct"] >= 50.0]["mean"].to_numpy()
        assert 50.0 <= np.nanmax(swing) <= 75.0


def test_build_scalar_bands() -> None:
    rng = np.random.default_rng(0)
    strides = pd.DataFrame(
        {
            "subject_id": np.repeat([f"S{i}" for i in range(8)], 4),
            "speed_class": "comfortable",
            "stance_pct": 60.0 + rng.normal(0, 1, 32),
            "cadence_steps_min": 112.0 + rng.normal(0, 4, 32),
            "step_length_m": 0.65 + rng.normal(0, 0.03, 32),
        }
    )
    bands = nb.build_scalar_bands(strides, dataset="test")
    assert set(bands["channel"]) == {"stance_pct", "cadence_steps_min", "step_length_m"}
    assert (bands["kind"] == "scalar").all()
    assert bands["pct"].isna().all()
    assert (bands["n_subjects"] == 8).all()
    assert (bands["n_curves"] == 32).all()
    stance = bands[bands["channel"] == "stance_pct"].iloc[0]
    assert 58.0 <= stance["mean"] <= 62.0


# ----------------------------------------------------------------------- round trip / IO
def test_save_and_load_roundtrip(fukuchi_root: Path, tmp_path: Path) -> None:
    bands, edges = _build_from_fixture(fukuchi_root)
    meta = nb.normband_metadata(
        bands,
        datasets=[{"key": "fukuchi2018", "citation": "Fukuchi 2018", "license": "CC BY 4.0"}],
        froude_edges={"fukuchi2018": edges},
        script_version="test",
    )
    out_dir = tmp_path / "out"
    path = nb.save_normbands(bands, meta, out_dir)
    assert path.exists()
    loaded = nb.load_normbands(dataset="fukuchi2018", data_dir=out_dir)
    assert loaded
    for key, band in loaded.items():
        assert isinstance(band, NormBand)
        assert band.mean.shape == (N_POINTS,)
        assert band.sd.shape == (N_POINTS,)
        assert band.n >= 1
        assert "Fukuchi" in band.source
        assert key == f"{band.meta['channel']}@{band.meta['speed_class']}"


# ------------------------------------------------------------- the bands shipped in-tree
@pytest.fixture(scope="module")
def shipped() -> dict[str, NormBand]:
    if not (nb.DATA_DIR / nb.PARQUET_NAME).exists():
        pytest.skip("normbands_v1.parquet not built; run scripts/build_normbands.py")
    return nb.load_normbands()


def test_shipped_bands_cover_the_schema_channels(shipped: dict[str, NormBand]) -> None:
    channels = {band.meta["channel"] for band in shipped.values()}
    assert channels <= set(ANGLE_CHANNELS)
    assert set(SIDED_CHANNELS) <= channels
    for channel in SIDED_CHANNELS:
        for speed_class in nb.SPEED_CLASSES:
            assert f"{channel}@{speed_class}" in shipped


def test_shipped_bands_have_101_points_and_a_source(shipped: dict[str, NormBand]) -> None:
    for key, band in shipped.items():
        assert band.mean.shape == (N_POINTS,), key
        assert band.sd.shape == (N_POINTS,), key
        assert band.unit == "deg"
        assert band.source and band.source != band.meta["dataset"]
        assert band.n >= 20


def test_shipped_bands_are_clinically_plausible(shipped: dict[str, NormBand]) -> None:
    for speed_class in nb.SPEED_CLASSES:
        knee = shipped[f"knee_flexion_deg@{speed_class}"]
        assert 55.0 <= knee.mean[50:].max() <= 70.0
        assert abs(knee.mean[0]) < 12.0  # near-extension at initial contact
        hip = shipped[f"hip_flexion_deg@{speed_class}"]
        assert 20.0 <= hip.mean[0] <= 45.0
        assert hip.mean.min() < 0.0  # hip extends in terminal stance


def test_shipped_scalar_bands(shipped: dict[str, NormBand]) -> None:
    scalars = nb.load_normbands(kind="scalar")
    for speed_class in nb.SPEED_CLASSES:
        assert 56.0 <= scalars[f"stance_pct@{speed_class}"].mean[0] <= 64.0
        assert 12.0 <= scalars[f"double_support_pct@{speed_class}"].mean[0] <= 30.0
        assert 90.0 <= scalars[f"cadence_steps_min@{speed_class}"].mean[0] <= 135.0
    assert (
        scalars["cadence_steps_min@slow"].mean[0]
        < scalars["cadence_steps_min@comfortable"].mean[0]
        < scalars["cadence_steps_min@fast"].mean[0]
    )


def test_shipped_file_is_small() -> None:
    if not (nb.DATA_DIR / nb.PARQUET_NAME).exists():
        pytest.skip("normbands_v1.parquet not built")
    assert (nb.DATA_DIR / nb.PARQUET_NAME).stat().st_size < 5 * 1024 * 1024


def test_metadata_records_licenses() -> None:
    if not (nb.DATA_DIR / nb.JSON_NAME).exists():
        pytest.skip("normbands_v1.json not built")
    meta = nb.read_normband_metadata()
    assert meta["n_points"] == N_POINTS
    assert meta["datasets"]
    for dataset in meta["datasets"]:
        assert dataset["license"] in {"CC BY 4.0", "CC0 1.0"}
        assert dataset["doi"]

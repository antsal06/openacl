"""Parser tests for the ``.trc``/``.mot`` readers, against tiny fixtures derived from a real
Sports2D run on the bundled demo video (see the work-package report for how they were made:
verbatim lines 1-5 plus a few data rows from ``lightweight`` mode with
``interp_gap_smaller_than=0``, ``fill_large_gaps_with='nan'``)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from openacl.backends._trc_mot import read_mot, read_trc

FIXTURES = Path(__file__).parent / "fixtures"


def test_read_trc_header_and_shape() -> None:
    trc = read_trc(FIXTURES / "demo_px_person00.trc")
    assert trc.fps == pytest.approx(30.0)
    assert trc.units == "m"  # Sports2D always writes 'm' in the header, even for px files
    assert trc.time_s.shape == (4,)
    assert trc.time_s[0] == pytest.approx(0.0)
    assert trc.time_s[-1] == pytest.approx(41 / 30)


def test_read_trc_marker_names() -> None:
    trc = read_trc(FIXTURES / "demo_px_person00.trc")
    assert "RHip" in trc.markers
    assert "LBigToe" in trc.markers
    assert "Hip" in trc.markers  # unsided pelvis point, not part of the schema mapping


def test_read_trc_nan_gap_then_valid_values() -> None:
    trc = read_trc(FIXTURES / "demo_px_person00.trc")
    r_hip = trc.markers["RHip"]
    assert r_hip.shape == (4, 3)
    # First two frames: person not yet detected -> NaN sentinel resolved to real NaN for X/Y.
    # Z is always the literal 0.0 placeholder Sports2D writes for 2-D (px) data, never NaN.
    assert np.isnan(r_hip[0, :2]).all()
    assert np.isnan(r_hip[1, :2]).all()
    # Frames 3-4: detected, real pixel coordinates.
    assert not np.isnan(r_hip[2]).any()
    assert r_hip[2, 0] == pytest.approx(1559.564089927, abs=1e-6)
    # Z is always the literal 0.0 placeholder for 2-D (px) files, never NaN.
    assert r_hip[:, 2].tolist() == [0.0, 0.0, 0.0, 0.0]


def test_read_mot_header_and_shape() -> None:
    mot = read_mot(FIXTURES / "demo_angles_person00.mot")
    assert mot.time_s.shape == (4,)
    assert "right knee" in mot.angles
    assert "left hip" in mot.angles


def test_read_mot_nan_gap_then_valid_values() -> None:
    mot = read_mot(FIXTURES / "demo_angles_person00.mot")
    right_knee = mot.angles["right knee"]
    assert np.isnan(right_knee[0])
    assert np.isnan(right_knee[1])
    assert right_knee[2] == pytest.approx(-11.034798115136994)
    assert right_knee[3] == pytest.approx(-9.877891653993945)
    # A single missing value in an otherwise valid row (right ankle at frame 4).
    right_ankle = mot.angles["right ankle"]
    assert right_ankle[2] == pytest.approx(14.524611019503624)
    assert np.isnan(right_ankle[3])

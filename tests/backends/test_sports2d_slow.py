"""Full Sports2D engine run on the bundled demo video: slow (seconds, downloads models on first
use), so gated behind ``@pytest.mark.slow`` / ``pytest --runslow tests/backends``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

sports2d = pytest.importorskip("Sports2D")

from openacl.backends.sports2d import run_sports2d
from openacl.schema import KinematicsResult

DEMO_VIDEO = Path(sports2d.__file__).parent / "Demo" / "demo.mp4"


@pytest.mark.slow
@pytest.mark.skipif(not DEMO_VIDEO.exists(), reason="sports2d demo.mp4 not available")
def test_run_sports2d_lightweight_on_demo(tmp_path: Path) -> None:
    result = run_sports2d(DEMO_VIDEO, tmp_path, mode="lightweight")

    assert isinstance(result, KinematicsResult)
    assert result.backend == "sports2d"
    assert result.fps == pytest.approx(30.0)
    assert result.keypoint_unit == "px"
    result.validate()

    for name in (
        "knee_flexion_deg_L",
        "knee_flexion_deg_R",
        "hip_flexion_deg_L",
        "hip_flexion_deg_R",
        "ankle_dorsiflexion_deg_L",
        "ankle_dorsiflexion_deg_R",
    ):
        assert name in result.angles_deg
        assert np.any(~np.isnan(result.angles_deg[name])), f"{name} is all-NaN"

    # Clinical sign sanity, loose bounds (this is a real, noisy demo run, not a fixed fixture).
    knee = np.concatenate(
        [result.angles_deg["knee_flexion_deg_L"], result.angles_deg["knee_flexion_deg_R"]]
    )
    knee = knee[~np.isnan(knee)]
    assert np.nanmax(knee) > 30.0  # swing-phase peak flexion
    assert np.nanmin(knee) > -30.0  # no absurd hyperextension

    assert result.walking_direction in ("+x", "-x", "unknown")
    assert result.camera_near_side in ("L", "R", None)

    assert (tmp_path / "kinematics.npz").exists()
    assert (tmp_path / "kinematics.json").exists()

    reloaded = KinematicsResult.load(tmp_path / "kinematics")
    assert reloaded.backend == "sports2d"
    assert reloaded.n_frames == result.n_frames

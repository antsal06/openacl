"""A fake session on disk: ``meta.yaml`` plus cached synthetic kinematics, no video needed.

``openacl.session.model.discover_passes`` also finds passes that exist only as
``derived/<pass>/kinematics.npz``, so the whole session pipeline can run without Sports2D and
without a single frame of video. The synthetic generator supplies a known ground truth, which
is what the pooling, symmetry and flag tests assert against.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from openacl.schema import Side
from tests.core.synthetic import SyntheticGaitConfig, make_synthetic_gait

N_PASSES = 6
"""Enough passes to alternate the walking direction three times per side."""

PEAK_KNEE_SWING_L_DEG = 60.0
PEAK_KNEE_SWING_R_DEG = 45.0
"""15 deg asymmetry -- deliberately above the 9.2 deg literature MDC for peak knee flexion."""

PEAK_KNEE_STANCE_DEG = 15.0
"""Identical on both sides, so the loading-response peak must come out below its MDC."""


@dataclass(frozen=True)
class FakeSession:
    """Where the fake session lives and what was put into it."""

    root: Path
    data_dir: Path
    pass_names: tuple[str, ...]
    near_side_of_pass: dict[str, Side]
    operated_side: Side
    height_m: float


def _meta_document(operated_side: Side, height_m: float) -> dict:
    return {
        "date": "2026-09-05",
        "time": "19:30",
        "post_op_weeks": 26,
        "subject": {
            "height_m": height_m,
            "mass_kg": 75,
            "operated_side": operated_side,
            "surgery_date": "2026-03-01",
            "graft": "STG (Hamstring)",
        },
        "location": "Flur Keller",
        "shoes": "Laufschuh X",
        "pain_now_0_10": 1,
        "pain_contra_0_10": 0,
        "fatigue_0_10": 2,
        "sleep_hours": 7,
        "activity_yesterday": "Rad 40 min",
        "notes": "",
        "cameras": {
            "A": {"device": "iPhone 15", "position": "sagittal, 4.5 m", "fps": 60},
            "B": {"device": "iPhone 13", "position": "45 Grad Wegende", "fps": 60},
        },
    }


def build_fake_session(
    root: Path,
    *,
    n_passes: int = N_PASSES,
    operated_side: Side = "R",
    height_m: float = 1.80,
    peak_knee_swing_r_deg: float = PEAK_KNEE_SWING_R_DEG,
    speed_m_s: float = 1.30,
    seed_offset: int = 0,
    with_camera_b: bool = True,
) -> FakeSession:
    """Write ``meta.yaml`` and one cached ``kinematics`` per pass under ``root``.

    Passes alternate their walking direction and their camera-near side, exactly as the
    recording protocol prescribes (10 passes, alternating). The right knee gets a smaller
    swing peak than the left, so the operated-side symmetry index must come out negative.
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "meta.yaml").write_text(
        yaml.safe_dump(
            _meta_document(operated_side, height_m), allow_unicode=True, sort_keys=False
        ),
        encoding="utf-8",
    )

    names: list[str] = []
    near_of_pass: dict[str, Side] = {}
    for index in range(1, n_passes + 1):
        near: Side = "R" if index % 2 == 1 else "L"
        name = f"A_pass{index:02d}"
        config = SyntheticGaitConfig(
            fps=60.0,
            n_cycles=6,
            unit="m",
            speed_m_s=speed_m_s,
            direction="+x" if near == "R" else "-x",
            camera_near_side=near,
            confidence=0.95,
            confidence_far_side=0.5,
            peak_knee_stance_deg_L=PEAK_KNEE_STANCE_DEG,
            peak_knee_stance_deg_R=PEAK_KNEE_STANCE_DEG,
            peak_knee_swing_deg_L=PEAK_KNEE_SWING_L_DEG,
            peak_knee_swing_deg_R=peak_knee_swing_r_deg,
            noise_deg=0.2,
            seed=index + seed_offset,
        )
        result, _truth = make_synthetic_gait(config)
        result.meta["fake_session_pass"] = name
        target = root / "derived" / name / "kinematics"
        target.parent.mkdir(parents=True, exist_ok=True)
        result.save(target)
        names.append(name)
        near_of_pass[name] = near
        if with_camera_b:
            (root / f"B_pass{index:02d}.mov").write_bytes(b"not a real video")

    data_dir = root.parent.parent
    return FakeSession(
        root=root,
        data_dir=data_dir,
        pass_names=tuple(names),
        near_side_of_pass=near_of_pass,
        operated_side=operated_side,
        height_m=height_m,
    )


@pytest.fixture
def fake_session(tmp_path: Path) -> FakeSession:
    """A six-pass fake session under ``<tmp>/data/sessions/2026-09-05_1930``."""
    root = tmp_path / "data" / "sessions" / "2026-09-05_1930"
    return build_fake_session(root)


@pytest.fixture(scope="session")
def normbands() -> dict:
    """The norm bands shipped with the package (angle curves, Fukuchi 2018)."""
    from openacl.norm import load_normbands

    return load_normbands()


def runslow_enabled(config: pytest.Config) -> bool:
    """Whether the slow, backend-running tests of this package should execute.

    ``--runslow`` is registered by ``tests/backends/conftest.py``; registering it here as well
    would make ``pytest tests/session tests/backends`` fail with "option names already added".
    So this package reads the flag when it happens to exist and otherwise falls back to the
    environment variable::

        OPENACL_RUNSLOW=1 .venv/bin/pytest tests/session/test_session_slow.py -q
    """
    if config.getoption("--runslow", default=False):
        return True
    return os.environ.get("OPENACL_RUNSLOW", "").lower() not in ("", "0", "false", "no")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "slow: marks tests as slow (needs --runslow)")

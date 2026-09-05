"""Full session run on the bundled Sports2D demo video: backend, gait-core, JSON and report.

Slow (a real pose-estimation run, models are downloaded on first use), therefore gated behind
``@pytest.mark.slow`` plus an opt-in flag::

    OPENACL_RUNSLOW=1 .venv/bin/pytest tests/session/test_session_slow.py -q

The demo video is linked into a temporary session folder as ``A_pass01.mp4``, so nothing is
copied and the repository stays free of video data.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

from tests.session.conftest import runslow_enabled

DEMO_VIDEO = (
    Path(__file__).resolve().parents[2]
    / ".venv/lib/python3.12/site-packages/Sports2D/Demo/demo.mp4"
)

META = {
    "date": "2026-09-05",
    "time": "19:30",
    "post_op_weeks": 26,
    "subject": {"height_m": 1.70, "mass_kg": 70, "operated_side": "R"},
    "location": "Sports2D demo",
    "shoes": "demo",
    "pain_now_0_10": 0,
    "pain_contra_0_10": 0,
    "fatigue_0_10": 0,
    "sleep_hours": 8,
    "activity_yesterday": "",
    "notes": "Sports2D demo video, not a real recording",
    "cameras": {"A": {"device": "demo", "position": "sagittal", "fps": 30}},
}


def _link_demo(session_dir: Path, name: str = "A_pass01.mp4") -> Path:
    session_dir.mkdir(parents=True, exist_ok=True)
    target = session_dir / name
    try:
        os.symlink(DEMO_VIDEO, target)
    except OSError:
        target.write_bytes(DEMO_VIDEO.read_bytes())
    return target


@pytest.mark.slow
def test_full_session_on_the_demo_video(tmp_path: Path, request: pytest.FixtureRequest) -> None:
    if not runslow_enabled(request.config):
        pytest.skip("needs --runslow or OPENACL_RUNSLOW=1")
    if not DEMO_VIDEO.exists():
        pytest.skip(f"Sports2D demo video not found at {DEMO_VIDEO}")

    from openacl.norm import load_normbands
    from openacl.session.aggregate import aggregate_session
    from openacl.session.model import load_session
    from openacl.session.process import process_session
    from openacl.session.report import write_report
    from openacl.session.wording import check_wording

    root = tmp_path / "data" / "sessions" / "2026-09-05_1930"
    _link_demo(root)
    (root / "meta.yaml").write_text(yaml.safe_dump(META, allow_unicode=True), encoding="utf-8")

    session = load_session(root)
    assert [p.name for p in session.passes_a] == ["A_pass01"]
    assert session.passes_a[0].has_video

    normbands = load_normbands()
    results = process_session(session, mode="lightweight", normbands=normbands)
    assert len(results) == 1
    outcome = results[0]
    assert outcome.error is None, outcome.error
    assert outcome.cached is False
    assert outcome.kinematics is not None
    assert outcome.kinematics.keypoint_unit == "m"  # subject.height_m enables to_meters
    assert "knee_flexion_deg_L" in outcome.kinematics.angles_deg
    assert (root / "derived" / "A_pass01" / "kinematics.npz").exists()

    summary = aggregate_session(session, results, normbands=normbands)
    json_path = summary.write_json(session.derived_dir / "session.json")
    # strict parse: a bare NaN/Infinity token would raise here
    json.loads(
        json_path.read_text(encoding="utf-8"),
        parse_constant=lambda token: pytest.fail(f"session.json contains {token}"),
    )
    assert summary.speed_class in ("slow", "comfortable", "fast")
    assert summary.quality["n_passes_ok"] == 1

    paths = write_report(summary, session.derived_dir)
    text = paths.markdown.read_text(encoding="utf-8")
    assert check_wording(text) == []
    assert "## Beobachtungen" in text
    assert paths.figures  # the real backend delivers knee, hip and ankle

    # a second run must hit the cache instead of re-running the backend
    cached = process_session(session, mode="lightweight", normbands=normbands)
    assert cached[0].cached is True
    assert cached[0].runtime_s < outcome.runtime_s


@pytest.mark.slow
def test_hevc_mov_is_handled(tmp_path: Path, request: pytest.FixtureRequest) -> None:
    """An HEVC ``.mov`` (what an iPhone records) must run through, transcoding if needed."""
    if not runslow_enabled(request.config):
        pytest.skip("needs --runslow or OPENACL_RUNSLOW=1")
    if not DEMO_VIDEO.exists():
        pytest.skip(f"Sports2D demo video not found at {DEMO_VIDEO}")
    import shutil
    import subprocess

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("ffmpeg not installed")

    root = tmp_path / "data" / "sessions" / "hevc"
    root.mkdir(parents=True)
    hevc = root / "A_pass01.mov"
    completed = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(DEMO_VIDEO),
            "-t",
            "2",
            "-c:v",
            "libx265",
            "-tag:v",
            "hvc1",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(hevc),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        pytest.skip(f"ffmpeg has no libx265: {completed.stderr[-500:]}")

    from openacl.backends.video import can_decode, probe
    from openacl.session.model import load_session
    from openacl.session.process import process_session

    info = probe(hevc)
    assert info.codec.lower() in ("hvc1", "hev1", "hevc")

    (root / "meta.yaml").write_text(yaml.safe_dump(META, allow_unicode=True), encoding="utf-8")
    session = load_session(root)
    results = process_session(session, mode="lightweight")
    assert results[0].error is None, results[0].error
    # OpenCV on this machine decodes HEVC directly; the transcode is only a fallback
    assert results[0].transcoded is not can_decode(hevc)

"""Test-retest comparison of two sessions and the derived ``data/subject/mdc.yaml``."""

from __future__ import annotations

import math
from pathlib import Path

import pytest
import yaml

from openacl.session.aggregate import aggregate_session, load_subject_mdc
from openacl.session.compare import (
    compare_sessions,
    default_mdc_path,
    read_session_json,
    write_mdc_yaml,
)
from openacl.session.model import load_session
from openacl.session.process import process_session
from tests.session.conftest import build_fake_session


def _make_session_json(root: Path, normbands: dict, **kwargs) -> Path:
    build_fake_session(root, **kwargs)
    session = load_session(root)
    results = process_session(session, normbands=normbands)
    summary = aggregate_session(session, results, normbands=normbands)
    return summary.write_json(session.derived_dir / "session.json")


@pytest.fixture
def two_identical_sessions(tmp_path: Path, normbands: dict) -> tuple[Path, Path]:
    sessions = tmp_path / "data" / "sessions"
    a = sessions / "2026-09-05_1900"
    b = sessions / "2026-09-05_1945"
    _make_session_json(a, normbands)
    _make_session_json(b, normbands)
    return a, b


def test_identical_sessions_give_zero_difference(two_identical_sessions) -> None:
    a, b = two_identical_sessions
    result = compare_sessions(read_session_json(a), read_session_json(b))
    assert result.differences
    for diff in result.differences:
        assert diff.delta == pytest.approx(0.0, abs=1e-9)
        if diff.above_mdc is not None:
            assert diff.above_mdc is False


def test_identical_sessions_give_a_vanishing_mdc(two_identical_sessions) -> None:
    a, b = two_identical_sessions
    result = compare_sessions(read_session_json(a), read_session_json(b))
    reliability = result.reliability["peak_knee_flexion_swing_deg"]
    assert reliability.n_sessions == 2
    assert reliability.n_targets >= 2
    assert reliability.icc_2_1 == pytest.approx(1.0, abs=1e-6)
    assert reliability.mdc95 == pytest.approx(0.0, abs=1e-6)


def test_noisier_repeat_gives_a_larger_mdc(tmp_path: Path, normbands: dict) -> None:
    sessions = tmp_path / "data" / "sessions"
    a, b = sessions / "s1", sessions / "s2"
    _make_session_json(a, normbands)
    _make_session_json(b, normbands, seed_offset=100, peak_knee_swing_r_deg=48.0)
    result = compare_sessions(read_session_json(a), read_session_json(b))
    reliability = result.reliability["peak_knee_flexion_swing_deg"]
    assert reliability.mdc95 > 0
    assert math.isfinite(reliability.icc_2_1)
    swing = [d for d in result.differences if d.metric == "peak_knee_flexion_swing_deg"]
    assert any(abs(d.delta) > 1.0 for d in swing)


def test_mdc_yaml_is_written_with_provenance(two_identical_sessions, tmp_path: Path) -> None:
    a, b = two_identical_sessions
    result = compare_sessions(read_session_json(a), read_session_json(b))
    path = write_mdc_yaml(result, tmp_path / "subject" / "mdc.yaml")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert document["source"] == "eigene Wiederholungsmessung"
    assert document["schema"] == "openacl.subject_mdc.v1"
    assert len(document["sessions"]) == 2
    entry = document["parameters"]["peak_knee_flexion_swing_deg"]
    assert entry["unit"] == "°"
    assert entry["n_sessions"] == 2
    assert entry["n_targets"] >= 2
    assert entry["icc_2_1"] is not None
    assert entry["source"] == "eigene Wiederholungsmessung"
    assert "Durchgänge" in entry["note"]

    # and it is readable back by the aggregation layer
    table = load_subject_mdc(path)
    assert table["peak_knee_flexion_swing_deg"].origin == "own"


def test_default_mdc_path_is_next_to_the_data_folder(tmp_path: Path) -> None:
    session_dir = tmp_path / "data" / "sessions" / "2026-09-05_1930"
    session_dir.mkdir(parents=True)
    assert default_mdc_path(session_dir) == tmp_path / "data" / "subject" / "mdc.yaml"
    assert default_mdc_path(session_dir / "derived") == tmp_path / "data" / "subject" / "mdc.yaml"


def test_read_session_json_accepts_directory_or_file(two_identical_sessions) -> None:
    a, _b = two_identical_sessions
    from_dir = read_session_json(a)
    from_derived = read_session_json(a / "derived")
    from_file = read_session_json(a / "derived" / "session.json")
    assert from_dir == from_derived == from_file
    with pytest.raises(FileNotFoundError):
        read_session_json(a.parent / "nothing-here")


def test_cli_session_and_compare_run_end_to_end(tmp_path: Path, capsys) -> None:
    from openacl.cli import main

    sessions = tmp_path / "data" / "sessions"
    a, b = sessions / "2026-09-05_1900", sessions / "2026-09-05_1945"
    build_fake_session(a)
    build_fake_session(b, seed_offset=50)

    assert main(["session", str(a)]) == 0
    assert main(["session", str(b)]) == 0
    assert (a / "derived" / "session.json").exists()
    assert (a / "derived" / "report.md").exists()
    assert (a / "derived" / "curve_knee_flexion_deg.png").exists()

    assert main(["compare", str(a), str(b)]) == 0
    mdc_path = tmp_path / "data" / "subject" / "mdc.yaml"
    assert mdc_path.exists()
    out = capsys.readouterr().out
    assert "Pooled cycles" in out
    assert "above MDC" in out
    assert str(mdc_path) in out

    # the freshly written MDC is picked up by the next session run (from the cache)
    assert main(["session", str(a)]) == 0
    import json

    document = json.loads((a / "derived" / "session.json").read_text(encoding="utf-8"))
    entry = document["symmetry"]["peak_knee_flexion_swing_deg"]["mdc"]
    assert entry["origin"] == "own"


def test_cli_session_reports_a_missing_directory(tmp_path: Path) -> None:
    from openacl.cli import main

    assert main(["session", str(tmp_path / "nope")]) == 1

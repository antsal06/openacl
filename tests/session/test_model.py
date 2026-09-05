"""Session metadata parsing and pass discovery."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from openacl.session.model import discover_passes, load_session, parse_meta, read_meta
from tests.session.conftest import FakeSession


def test_meta_is_parsed_completely(fake_session: FakeSession) -> None:
    meta = read_meta(fake_session.root)
    assert meta.date == "2026-09-05"
    assert meta.post_op_weeks == 26
    assert meta.subject.height_m == pytest.approx(1.80)
    assert meta.subject.operated_side == "R"
    assert meta.subject.graft == "STG (Hamstring)"
    assert meta.camera_fps("A") == 60.0
    assert meta.warnings == ()


def test_missing_fields_warn_but_do_not_raise(tmp_path: Path) -> None:
    (tmp_path / "meta.yaml").write_text("date: 2026-09-05\n", encoding="utf-8")
    meta = read_meta(tmp_path)
    assert meta.date == "2026-09-05"
    assert meta.subject.height_m is None
    assert meta.subject.operated_side is None
    joined = " ".join(meta.warnings)
    assert "subject" in joined
    assert "post_op_weeks" in joined


def test_broken_subject_block_is_tolerated() -> None:
    meta = parse_meta({"subject": {"height_m": "sehr groß", "operated_side": "links"}})
    assert meta.subject.height_m is None
    assert meta.subject.operated_side is None
    assert any("operated_side" in w for w in meta.warnings)


def test_implausible_height_is_rejected() -> None:
    meta = parse_meta({"subject": {"height_m": 180}})
    assert meta.subject.height_m is None
    assert any("1.0-2.3" in w for w in meta.warnings)


def test_missing_meta_file_is_not_fatal(tmp_path: Path) -> None:
    meta = read_meta(tmp_path)
    assert meta.date is None
    assert any("no meta.yaml" in w for w in meta.warnings)


def test_broken_yaml_is_not_fatal(tmp_path: Path) -> None:
    (tmp_path / "meta.yaml").write_text("date: [unclosed\n", encoding="utf-8")
    meta = read_meta(tmp_path)
    assert any("could not be parsed" in w for w in meta.warnings)


def test_discovery_finds_cached_passes_and_lists_camera_b(fake_session: FakeSession) -> None:
    session = load_session(fake_session.root)
    assert [p.name for p in session.passes_a] == list(fake_session.pass_names)
    assert all(p.video is None for p in session.passes_a)
    assert [p.name for p in session.passes_b] == [
        f"B_pass{i:02d}" for i in range(1, len(fake_session.pass_names) + 1)
    ]
    assert any("camera-B" in w for w in session.warnings)
    assert session.derived_dir == fake_session.root / "derived"
    assert session.data_dir == fake_session.data_dir


def test_discovery_matches_video_suffixes_case_insensitively(tmp_path: Path) -> None:
    for name in ("A_pass01.MOV", "A_pass02.mp4", "B_pass01.mov", "notes.txt"):
        (tmp_path / name).write_bytes(b"x")
    passes, warnings = discover_passes(tmp_path)
    assert [p.name for p in passes] == ["A_pass01", "A_pass02", "B_pass01"]
    assert [p.camera for p in passes] == ["A", "A", "B"]
    assert passes[0].number == 1
    assert warnings == []


def test_badly_named_video_is_warned_about(tmp_path: Path) -> None:
    (tmp_path / "IMG_1234.mov").write_bytes(b"x")
    (tmp_path / "A_pass01.mov").write_bytes(b"x")
    _passes, warnings = discover_passes(tmp_path)
    assert any("IMG_1234" in w for w in warnings)


def test_session_without_camera_a_raises(tmp_path: Path) -> None:
    (tmp_path / "meta.yaml").write_text(yaml.safe_dump({"date": "2026-09-05"}), encoding="utf-8")
    (tmp_path / "B_pass01.mov").write_bytes(b"x")
    with pytest.raises(ValueError, match="no camera-A pass"):
        load_session(tmp_path)


def test_missing_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_session(tmp_path / "does-not-exist")

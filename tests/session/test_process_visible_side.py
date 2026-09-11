"""Tests for the ADR-0010 wiring in :func:`openacl.session.process.run_backend`:

- a segmented pass's ``passes.yaml`` direction is translated into Sports2D's ``visible_side``
  via ``meta.yaml`` ``cameras.A.near_side_when_walking_plus_x`` (default ``"R"``, with a
  session-level warning when the field is missing but ``passes.yaml`` exists);
- ``cameras.A.distance_m`` is passed through as Sports2D's perspective camera-to-person
  distance.

``run_sports2d`` itself is never invoked here (that needs the real ``sports2d`` package, see
``test_sports2d_slow.py``); it is replaced with a stand-in that records the keyword arguments it
was called with.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import yaml

import openacl.backends.sports2d as sports2d_module
import openacl.session.process as process_module
from openacl.schema import KinematicsResult
from openacl.session.model import load_session


def _write_session(
    root: Path,
    *,
    near_side_when_walking_plus_x: str | None = "R",
    direction: str = "+x",
    distance_m: float | None = None,
    with_passes_yaml: bool = True,
) -> Path:
    root.mkdir(parents=True)
    camera_a: dict = {"fps": 60}
    if near_side_when_walking_plus_x is not None:
        camera_a["near_side_when_walking_plus_x"] = near_side_when_walking_plus_x
    if distance_m is not None:
        camera_a["distance_m"] = distance_m
    (root / "meta.yaml").write_text(
        yaml.safe_dump(
            {
                "date": "2026-09-07",
                "subject": {"height_m": 1.80, "operated_side": "R"},
                "cameras": {"A": camera_a},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    if with_passes_yaml:
        (root / "passes.yaml").write_text(
            yaml.safe_dump(
                [
                    {
                        "t_start_s": 0.0,
                        "t_end_s": 4.0,
                        "duration_s": 3.7,
                        "direction": direction,
                        "drift_px": 200.0 if direction == "+x" else -200.0,
                        "mean_area": 0.05,
                        "file": "A_pass01.mp4",
                    }
                ],
                sort_keys=False,
            ),
            encoding="utf-8",
        )
    (root / "A_pass01.mp4").write_bytes(b"not a real video")
    return root


def _fake_ensure_decodable(video, pass_dir):
    return video, False, []


def _run_backend_capturing(monkeypatch: pytest.MonkeyPatch, session):
    captured: dict = {}

    def fake_run_sports2d(video, out_dir, **kwargs):
        captured.update(kwargs)
        return KinematicsResult(backend="sports2d", fps=30.0, time_s=np.array([0.0, 1.0]))

    monkeypatch.setattr(process_module, "_ensure_decodable", _fake_ensure_decodable)
    monkeypatch.setattr(sports2d_module, "run_sports2d", fake_run_sports2d)
    process_module.run_backend(session, session.passes_a[0])
    return captured


def test_plus_x_with_default_near_side_maps_to_right(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _write_session(tmp_path / "s", near_side_when_walking_plus_x="R", direction="+x")
    session = load_session(root)
    captured = _run_backend_capturing(monkeypatch, session)
    assert captured["visible_side"] == "right"


def test_minus_x_with_default_near_side_maps_to_left(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _write_session(tmp_path / "s", near_side_when_walking_plus_x="R", direction="-x")
    session = load_session(root)
    captured = _run_backend_capturing(monkeypatch, session)
    assert captured["visible_side"] == "left"


def test_near_side_config_is_inverted_when_plus_x_means_left(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _write_session(tmp_path / "s", near_side_when_walking_plus_x="L", direction="+x")
    session = load_session(root)
    captured = _run_backend_capturing(monkeypatch, session)
    assert captured["visible_side"] == "left"


def test_missing_near_side_config_defaults_to_r_and_warns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _write_session(tmp_path / "s", near_side_when_walking_plus_x=None, direction="+x")
    session = load_session(root)
    assert any("near_side_when_walking_plus_x" in w for w in session.meta.warnings)
    captured = _run_backend_capturing(monkeypatch, session)
    assert captured["visible_side"] == "right"  # default near side is 'R'


def test_no_passes_yaml_falls_back_to_auto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _write_session(tmp_path / "s", with_passes_yaml=False)
    session = load_session(root)
    # no passes.yaml -> the near-side warning specifically must not fire
    assert not any("near_side_when_walking_plus_x" in w for w in session.meta.warnings)
    captured = _run_backend_capturing(monkeypatch, session)
    assert captured["visible_side"] == "auto"


def test_camera_distance_is_passed_through_as_perspective_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _write_session(tmp_path / "s", distance_m=4.5)
    session = load_session(root)
    captured = _run_backend_capturing(monkeypatch, session)
    assert captured["extra_config"] == {"px_to_meters_conversion": {"perspective_value": 4.5}}


def test_no_camera_distance_means_no_extra_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _write_session(tmp_path / "s", distance_m=None)
    session = load_session(root)
    captured = _run_backend_capturing(monkeypatch, session)
    assert captured["extra_config"] is None

"""Tests for :mod:`openacl.backends.video`."""

from __future__ import annotations

from pathlib import Path

import pytest

from openacl.backends.video import probe

try:
    from Sports2D import __file__ as _sports2d_file

    DEMO_VIDEO = Path(_sports2d_file).parent / "Demo" / "demo.mp4"
except ImportError:
    DEMO_VIDEO = None


@pytest.mark.skipif(
    DEMO_VIDEO is None or not DEMO_VIDEO.exists(), reason="sports2d demo.mp4 not available"
)
def test_probe_demo_video() -> None:
    info = probe(DEMO_VIDEO)
    assert info.fps == pytest.approx(30.0, abs=1.0)
    assert info.width > 0
    assert info.height > 0
    assert info.n_frames > 0
    assert info.duration_s == pytest.approx(info.n_frames / info.fps)
    # Landscape, ~30fps demo video: expect the low-fps warning but not the portrait one.
    assert not any("portrait" in w for w in info.warnings)


def test_probe_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        probe(tmp_path / "does_not_exist.mp4")

"""Shared fixtures for openacl.health tests. No access to data/ anywhere here."""

from __future__ import annotations

from pathlib import Path

import pytest

from .synthetic import default_records, write_export_xml, write_export_zip


@pytest.fixture
def synthetic_records():
    return default_records()


@pytest.fixture
def export_xml_path(tmp_path: Path) -> Path:
    return write_export_xml(tmp_path / "export.xml")


@pytest.fixture
def export_zip_path(tmp_path: Path) -> Path:
    return write_export_zip(tmp_path / "export.zip")

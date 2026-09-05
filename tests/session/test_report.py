"""The rendered report: structure, numbers, figures and ADR-0004 wording."""

from __future__ import annotations

from pathlib import Path

import pytest

from openacl.session.aggregate import aggregate_session
from openacl.session.model import load_session
from openacl.session.process import process_session
from openacl.session.report import fmt, render_markdown, write_report
from openacl.session.wording import (
    FORBIDDEN_TERMS,
    check_wording,
    missing_hedges,
)
from tests.session.conftest import FakeSession


@pytest.fixture
def summary(fake_session: FakeSession, normbands: dict):
    session = load_session(fake_session.root)
    results = process_session(session, normbands=normbands)
    return session, aggregate_session(session, results, normbands=normbands)


@pytest.fixture
def report(summary, tmp_path: Path):
    _session, session_summary = summary
    paths = write_report(session_summary, tmp_path / "derived")
    return paths, paths.markdown.read_text(encoding="utf-8")


def test_report_contains_no_forbidden_wording(report) -> None:
    _paths, text = report
    findings = check_wording(text)
    assert findings == [], "\n".join(str(f) for f in findings)


def test_report_carries_the_required_hedges(report) -> None:
    _paths, text = report
    assert missing_hedges(text) == []


def test_wording_check_actually_catches_things() -> None:
    findings = check_wording("Das ist ein Defizit, du solltest eine Übung machen.")
    assert {f.term for f in findings} == {"defizit", "solltest", "übung"}
    assert all(f.line_number == 1 for f in findings)
    assert all(f.reason for f in findings)
    assert set(FORBIDDEN_TERMS) >= {"defizit", "patholog", "übung", "solltest", "du hast"}


def test_report_has_all_required_sections(report) -> None:
    _paths, text = report
    for heading in (
        "# Ganganalyse Session",
        "## Mittelkurven gegen Normband",
        "## Zeit-Weg-Parameter und diskrete Winkelwerte",
        "## Beobachtungen",
        "## Abstand zum Normband",
        "## Was dieses Video nicht sieht",
        "## Qualität",
    ):
        assert heading in text, heading


def test_not_visible_section_names_its_sources(report) -> None:
    _paths, text = report
    for source in ("Sajedi", "Noehren", "Wellsandt"):
        assert source in text
    for topic in ("Gelenkmomente", "Muskelaktivierung", "Gegenseite als Referenz"):
        assert topic in text


def test_table_has_the_mdc_verdict_column(report) -> None:
    _paths, text = report
    assert "| Differenz | SI (%) | MDC | Einordnung |" in text
    assert "über MDC" in text
    assert "unter MDC" in text


def test_observations_follow_the_prescribed_sentence_shape(report) -> None:
    _paths, text = report
    body = text.split("## Beobachtungen", 1)[1].split("## Abstand", 1)[0]
    sentences = [line for line in body.splitlines() if line.startswith("- ")]
    assert sentences
    for sentence in sentences:
        assert "operierte Seite:" in sentence
        assert "Gegenseite:" in sentence
        assert "MDC" in sentence
        assert "±" in sentence
    assert any("liegt über dem MDC" in s for s in sentences)
    assert any("liegt unter dem MDC" in s for s in sentences)


def test_figures_are_written_and_linked(report) -> None:
    paths, text = report
    # the synthetic generator produces knee and hip, but no ankle channel
    assert len(paths.figures) == 2
    for figure in paths.figures:
        assert figure.exists()
        assert figure.stat().st_size > 5_000
        assert f"]({figure.name})" in text
    assert "curve_knee_flexion_deg.png" in text


def test_quality_section_reports_counts_and_fps(report, summary) -> None:
    _paths, text = report
    _session, session_summary = summary
    quality = text.split("## Qualität", 1)[1]
    assert "Durchgänge: 6 von 6 ausgewertet." in quality
    assert "60,0 fps" in quality
    assert "Kamera B: 6 Durchgänge" in quality
    for side in ("L", "R"):
        assert f"Zyklen Seite {side}" in quality
    assert session_summary.quality["n_cycles"]["R"] > 0


def test_title_note_marks_synthetic_data(summary, tmp_path: Path) -> None:
    _session, session_summary = summary
    paths = write_report(session_summary, tmp_path / "note", title_note=" (synthetische Daten)")
    text = paths.markdown.read_text(encoding="utf-8")
    assert text.splitlines()[0].endswith("(synthetische Daten)")
    assert check_wording(text) == []


def test_german_number_formatting() -> None:
    assert fmt(1.234, 2) == "1,23"
    assert fmt(float("nan")) == "–"
    assert fmt(None) == "–"


def test_report_without_operated_side_stays_clean(summary, tmp_path: Path) -> None:
    _session, session_summary = summary
    session_summary.operated_side = None
    text = render_markdown(session_summary, [])
    assert "Seite R" in text
    assert check_wording(text) == []

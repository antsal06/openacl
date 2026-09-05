"""Forbidden wording in reports and UI (ADR-0004, EU MDR Regel 11).

The report describes **observations** and **hypotheses for discussion**, never a diagnosis, an
assessment or a therapeutic instruction. Software that supports diagnosis or therapy is a
class IIa medical device in the EU; staying descriptive keeps OpenACL out of that scope and,
more importantly, keeps it honest -- a smartphone video cannot support the claims the forbidden
words make.

The list is intentionally about *language*, not about numbers: reporting that the operated side
shows 6 degrees less peak knee flexion than the contralateral side is fine, calling that a
"Defizit" is not. :func:`check_wording` is used by the report test and can be run on any text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

FORBIDDEN_TERMS: dict[str, str] = {
    # diagnostic / evaluative vocabulary
    "defizit": "beschreibt eine Bewertung; stattdessen 'Unterschied' oder 'geringerer Wert'",
    "patholog": "diagnostische Zuschreibung; stattdessen 'Beobachtung' mit Zahl und Quelle",
    "diagnos": "Diagnose ist der Interpretationsschicht verboten (ADR-0004)",
    "auffällig": "wertend; stattdessen 'liegt über dem MDC' mit Zahl",
    "abnorm": "wertend; stattdessen 'außerhalb des Normbands (± 2 SD)'",
    "krankhaft": "diagnostische Zuschreibung",
    "störung": "diagnostische Zuschreibung; stattdessen 'Unterschied' oder 'Muster'",
    "beeinträchtig": "wertend; stattdessen die gemessene Differenz nennen",
    "schwäche": "diagnostische Zuschreibung; Video misst keine Kraft",
    "insuffizien": "diagnostische Zuschreibung",
    "instabil": "klinischer Befund, aus Video nicht belegbar",
    "gesunde seite": "die Gegenseite ist nach ACLR keine gesunde Referenz (Wellsandt 2017)",
    # therapeutic instructions
    "übung": "Therapieempfehlung; der Report empfiehlt nichts (ADR-0004)",
    "therapi": "Therapieempfehlung; nur 'Hypothese zur Besprechung mit Fachpersonal'",
    "behandl": "Therapieempfehlung",
    "trainiere": "Therapieempfehlung",
    "solltest": "Handlungsanweisung an die Person",
    "du hast": "diagnostische Ansprache; stattdessen 'die Messung zeigt'",
    "du musst": "Handlungsanweisung an die Person",
    "empfehlen wir": "Empfehlung; der Report beobachtet nur",
    "empfehlung": "Empfehlung; der Report beobachtet nur",
    "muss korrigiert": "Handlungsanweisung",
    "korrigiere": "Handlungsanweisung",
}
"""Lowercased substring -> why it is not allowed. Substrings so that inflections are caught."""

REQUIRED_HEDGES: tuple[str, ...] = (
    "Beobachtung",
    "Hypothese zur Besprechung",
)
"""Phrases every generated report must contain, so its framing stays explicit."""


@dataclass(frozen=True)
class WordingFinding:
    """One hit of a forbidden term, with enough context to fix it."""

    term: str
    reason: str
    line_number: int
    line: str

    def __str__(self) -> str:
        return f"line {self.line_number}: {self.term!r} -- {self.reason} | {self.line.strip()}"


def check_wording(text: str, terms: dict[str, str] | None = None) -> list[WordingFinding]:
    """Return every forbidden-term hit in ``text``; an empty list means the text is clean."""
    table = FORBIDDEN_TERMS if terms is None else terms
    findings: list[WordingFinding] = []
    for number, line in enumerate(text.splitlines(), start=1):
        lowered = line.lower()
        for term, reason in table.items():
            if term in lowered:
                findings.append(
                    WordingFinding(term=term, reason=reason, line_number=number, line=line)
                )
    return findings


def missing_hedges(text: str, hedges: tuple[str, ...] = REQUIRED_HEDGES) -> list[str]:
    """Return the required framing phrases that ``text`` does not contain."""
    return [hedge for hedge in hedges if hedge.lower() not in text.lower()]


def assert_clean(text: str) -> None:
    """Raise ``ValueError`` listing every forbidden term found in ``text``."""
    findings = check_wording(text)
    if findings:
        joined = "\n".join(str(f) for f in findings)
        raise ValueError(f"text contains wording forbidden by ADR-0004:\n{joined}")


_WHITESPACE = re.compile(r"\s+")


def normalise(text: str) -> str:
    """Collapse whitespace; handy when checking a rendered table cell."""
    return _WHITESPACE.sub(" ", text).strip()

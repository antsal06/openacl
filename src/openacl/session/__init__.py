"""Session layer (ADR-0009): a folder of walking passes plus metadata, pooled into one report.

A session is a directory ``data/sessions/YYYY-MM-DD_HHMM/`` holding ``meta.yaml``, the camera-A
videos ``A_pass01.mov`` ... and (optionally) camera-B videos. Everything this layer derives
lands in ``<session>/derived/``: one folder per pass with the cached ``kinematics.npz``, plus
``session.json`` and ``report.md`` with its PNGs.

Nothing here is diagnostic: the report speaks of observations and hypotheses for discussion
(ADR-0004), and every difference is put next to the minimal detectable change (ADR-0003).
"""

from openacl.session.aggregate import (
    METRICS,
    MetricSpec,
    PooledCycles,
    SessionSummary,
    aggregate_session,
    load_subject_mdc,
    symmetry_index_operated_pct,
)
from openacl.session.compare import CompareResult, compare_sessions, write_mdc_yaml
from openacl.session.model import (
    PassFile,
    Session,
    SessionMeta,
    SessionSubject,
    load_session,
)
from openacl.session.process import PassResult, process_session
from openacl.session.report import write_report
from openacl.session.wording import FORBIDDEN_TERMS, WordingFinding, check_wording

__all__ = [
    "FORBIDDEN_TERMS",
    "METRICS",
    "CompareResult",
    "MetricSpec",
    "PassFile",
    "PassResult",
    "PooledCycles",
    "Session",
    "SessionMeta",
    "SessionSubject",
    "SessionSummary",
    "WordingFinding",
    "aggregate_session",
    "check_wording",
    "compare_sessions",
    "load_session",
    "load_subject_mdc",
    "process_session",
    "symmetry_index_operated_pct",
    "write_mdc_yaml",
    "write_report",
]

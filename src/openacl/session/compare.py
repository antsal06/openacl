"""Compare two sessions and derive the subject's own MDC95 (ADR-0009).

Design of the reliability estimate: the **targets** are the individual passes of a session
(``per_pass`` in ``session.json``), the **repetitions** are the two sessions. That follows the
clinical test-retest logic and deliberately does not use single cycles as targets, because
cycles within one pass are correlated and would make the measurement look better than it is.
Left and right enter the matrix as separate rows of the same parameter, which doubles the
number of targets without pretending the two limbs are independent measurements of one thing --
they are two targets measured twice each, exactly what ICC(2,1) expects.

The result is written to ``data/subject/mdc.yaml`` and is preferred over the literature values
in :data:`openacl.core.mdc.DEFAULT_MDC` by every later session
(:func:`openacl.session.aggregate.load_subject_mdc`).
"""

from __future__ import annotations

import datetime as _dt
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from openacl.core.events import SIDES
from openacl.core.mdc import ReliabilityResult, reliability_from_repeats
from openacl.session.aggregate import MDC_SOURCE_OWN, METRICS, METRICS_BY_NAME

MDC_YAML_NAME = "mdc.yaml"
MIN_TARGETS = 2
"""ICC(2,1) needs at least two targets (pass x side rows) present in both sessions."""


@dataclass(frozen=True)
class MetricDifference:
    """One key figure in both sessions and the difference between them."""

    metric: str
    side: str
    unit: str
    value_a: float
    value_b: float
    delta: float
    """``B - A``."""
    mdc95: float | None
    above_mdc: bool | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "side": self.side,
            "unit": self.unit,
            "value_a": self.value_a,
            "value_b": self.value_b,
            "delta_b_minus_a": self.delta,
            "mdc95": self.mdc95,
            "above_mdc": self.above_mdc,
        }


@dataclass(eq=False)
class CompareResult:
    """Session-level differences plus the reliability of every key figure."""

    session_a: str
    session_b: str
    differences: list[MetricDifference] = field(default_factory=list)
    reliability: dict[str, ReliabilityResult] = field(default_factory=dict)
    n_targets: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_a": self.session_a,
            "session_b": self.session_b,
            "differences": [d.to_dict() for d in self.differences],
            "reliability": {
                name: {
                    "icc_2_1": r.icc_2_1,
                    "sem": r.sem,
                    "mdc95": r.mdc95,
                    "sd_pooled": r.sd_pooled,
                    "n_targets": r.n_targets,
                    "n_sessions": r.n_sessions,
                    "unit": r.unit,
                    "source": r.source,
                }
                for name, r in self.reliability.items()
            },
            "warnings": self.warnings,
        }


def read_session_json(path: Path | str) -> dict[str, Any]:
    """Read a ``session.json``; accepts either the file or the session/derived directory."""
    path = Path(path).expanduser().resolve()
    if path.is_dir():
        for candidate in (path / "session.json", path / "derived" / "session.json"):
            if candidate.exists():
                path = candidate
                break
        else:
            raise FileNotFoundError(
                f"no session.json in {path} or {path / 'derived'}; run `openacl session` first"
            )
    return json.loads(path.read_text(encoding="utf-8"))


def _finite(value: Any) -> float:
    """JSON stores non-finite numbers as ``null``; turn everything back into a float."""
    if value is None:
        return float("nan")
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return out if math.isfinite(out) else float("nan")


def _pass_matrix(
    session_a: dict[str, Any], session_b: dict[str, Any], metric: str
) -> tuple[np.ndarray, list[str]]:
    """``(n_targets, 2)`` matrix of one metric; targets are ``pass x side`` present in both."""
    by_name_a = {p["name"]: p for p in session_a.get("per_pass", [])}
    by_name_b = {p["name"]: p for p in session_b.get("per_pass", [])}
    rows: list[list[float]] = []
    labels: list[str] = []
    for name in sorted(set(by_name_a) & set(by_name_b)):
        for side in SIDES:
            a = _finite((by_name_a[name].get("metrics", {}).get(side) or {}).get(metric))
            b = _finite((by_name_b[name].get("metrics", {}).get(side) or {}).get(metric))
            if np.isfinite(a) and np.isfinite(b):
                rows.append([a, b])
                labels.append(f"{name}:{side}")
    return np.asarray(rows, dtype=float).reshape(-1, 2), labels


def compare_sessions(session_a: dict[str, Any], session_b: dict[str, Any]) -> CompareResult:
    """Difference per key figure plus ICC(2,1)/SEM/MDC95 from the per-pass repeat design."""
    result = CompareResult(
        session_a=str(session_a.get("session_dir", "A")),
        session_b=str(session_b.get("session_dir", "B")),
    )
    if session_a.get("pooling") != session_b.get("pooling"):
        result.warnings.append(
            f"die Sessions wurden unterschiedlich gepoolt "
            f"({session_a.get('pooling')} vs. {session_b.get('pooling')}); "
            "der Vergleich mischt damit zwei Auswertungsarten"
        )
    if session_a.get("operated_side") != session_b.get("operated_side"):
        result.warnings.append("die Sessions nennen unterschiedliche operierte Seiten im meta.yaml")

    for spec in METRICS:
        matrix, _labels = _pass_matrix(session_a, session_b, spec.name)
        result.n_targets[spec.name] = matrix.shape[0]
        if matrix.shape[0] < MIN_TARGETS:
            result.warnings.append(
                f"{spec.name}: nur {matrix.shape[0]} gemeinsame Durchgang-Seiten-Paare, "
                f"für ICC und MDC95 sind mindestens {MIN_TARGETS} nötig"
            )
            continue
        result.reliability[spec.name] = reliability_from_repeats(matrix, unit=spec.unit)

    for spec in METRICS:
        for side in SIDES:
            a = _finite(
                (session_a.get("metrics", {}).get(spec.name, {}).get(side) or {}).get("mean")
            )
            b = _finite(
                (session_b.get("metrics", {}).get(spec.name, {}).get(side) or {}).get("mean")
            )
            if not (np.isfinite(a) or np.isfinite(b)):
                continue
            delta = b - a
            reliability = result.reliability.get(spec.name)
            mdc95 = reliability.mdc95 if reliability is not None else None
            above = (
                bool(abs(delta) > abs(mdc95))
                if mdc95 is not None and np.isfinite(delta) and np.isfinite(mdc95)
                else None
            )
            result.differences.append(
                MetricDifference(
                    metric=spec.name,
                    side=side,
                    unit=spec.unit,
                    value_a=a,
                    value_b=b,
                    delta=delta,
                    mdc95=mdc95,
                    above_mdc=above,
                )
            )
    return result


def default_mdc_path(session_dir: Path | str) -> Path:
    """``<data>/subject/mdc.yaml`` for a session laid out as ``data/sessions/<name>``."""
    root = Path(session_dir).expanduser().resolve()
    if root.name == "derived":
        root = root.parent
    parent = root.parent
    data_dir = parent.parent if parent.name == "sessions" else parent
    return data_dir / "subject" / MDC_YAML_NAME


def write_mdc_yaml(result: CompareResult, path: Path | str) -> Path:
    """Write the derived MDC95 values, with ICC, n and provenance, to ``path``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    parameters: dict[str, Any] = {}
    for name, reliability in sorted(result.reliability.items()):
        if not math.isfinite(reliability.mdc95):
            continue
        spec = METRICS_BY_NAME.get(name)
        parameters[name] = {
            "value": round(float(reliability.mdc95), 4),
            "unit": spec.unit if spec else reliability.unit,
            "icc_2_1": round(float(reliability.icc_2_1), 4)
            if math.isfinite(reliability.icc_2_1)
            else None,
            "sem": round(float(reliability.sem), 4),
            "n_targets": int(reliability.n_targets),
            "n_sessions": int(reliability.n_sessions),
            "source": MDC_SOURCE_OWN,
            "note": (
                "Durchgänge × Seiten als Targets, Sessions als Wiederholungen; "
                "ICC(2,1) nach Shrout & Fleiss 1979, MDC95 = 1,96 × √2 × SEM (Weir 2005)"
            ),
        }
    document = {
        "schema": "openacl.subject_mdc.v1",
        "date": _dt.datetime.now(_dt.UTC).date().isoformat(),
        "source": MDC_SOURCE_OWN,
        "sessions": [result.session_a, result.session_b],
        "design": (
            "Test-Retest über zwei Sessions am selben Tag; Targets sind die einzelnen "
            "Durchgänge je Seite, Wiederholungen die beiden Sessions (ADR-0009)"
        ),
        "parameters": parameters,
    }
    path.write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    return path

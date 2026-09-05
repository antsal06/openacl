"""Render ``derived/report.md`` plus its PNGs from a :class:`SessionSummary`.

Language rules (ADR-0004, enforced by :mod:`openacl.session.wording` and its test): every
statement is an observation with its number, its unit and its source; a side difference is only
called out when it exceeds the minimal detectable change; nothing is recommended, assessed or
diagnosed. The report is German, the code and the identifiers are English (CLAUDE.md).

Figures: one PNG per angle channel with the session mean curve +- 1 SD per side against the
norm band mean +- 1 SD (norm band grey, operated side coloured and solid, contralateral side
dashed).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from openacl.core.events import SIDES
from openacl.schema import Side
from openacl.session.aggregate import (
    CHANNEL_LABELS_DE,
    CURVE_CHANNELS,
    METRICS,
    Estimate,
    SessionSummary,
    other_side,
)

REPORT_NAME = "report.md"

OPERATED_COLOR = "#c1272d"
CONTRA_COLOR = "#1f5fa9"
NORM_COLOR = "#8a8a8a"

NOT_VISIBLE_TEXT = """Ein einzelnes Video aus der Seitenansicht misst Winkel, Zeiten und Wege.
Drei Dinge, die für den Verlauf nach einer Kreuzbandplastik wichtig sind, bleiben dabei außerhalb
der Messung:

- **Gelenkmomente und Kräfte.** Das äußere Knieflexionsmoment ist nach ACLR über Jahre
  verändert (Peak Knieextensormoment beim Gehen 0,04 ± 0,2 gegenüber 0,23 ± 0,1 Nm/kg·m bei
  Kontrollpersonen, p < 0,001, fünf Jahre nach der Operation), ohne dass sich die Winkelkurve
  entsprechend deutlich unterscheidet (Noehren, Wilson, Miller, Lattermann 2013, *Med Sci Sports
  Exerc* 45(7):1340-1347; Sajedi et al. 2025, *Healthcare* 13(24):3304). Momente brauchen eine
  Kraftmessplatte, kein Video kann sie ersetzen.
- **Muskelaktivierung.** Wie stark und wann Quadrizeps und ischiocrurale Muskulatur aktiv sind,
  ist aus der Körperkontur nicht ablesbar. Genau dort liegt aber ein großer Teil dessen, was sich
  nach einer Kreuzbandplastik anders anfühlt (Oberflächen-EMG wäre die passende Messgröße,
  siehe ADR-0005).
- **Die Gegenseite als Referenz.** Der Seitenvergleich unterstellt, dass die nicht operierte
  Seite unverändert ist. Nach ACLR verändert sie sich mit, deshalb kann ein Symmetriewert nahe
  null die Situation günstiger erscheinen lassen, als sie ist (Wellsandt, Failla,
  Snyder-Mackler 2017, *JOSPT*, DOI 10.2519/jospt.2017.7285).

Alle Angaben in diesem Dokument sind Beobachtungen aus der Videomessung und Hypothesen zur
Besprechung mit Fachpersonal, keine Aussage über Gesundheitszustand oder Vorgehen."""

TABLE_METRIC_ORDER: tuple[str, ...] = (
    "stance_pct",
    "swing_pct",
    "double_support_pct",
    "stride_time_s",
    "cadence_steps_per_min",
    "step_length_m",
    "stride_length_m",
    "walking_speed_m_s",
    "knee_flexion_at_initial_contact_deg",
    "peak_knee_flexion_loading_deg",
    "min_knee_flexion_midstance_deg",
    "peak_knee_flexion_swing_deg",
    "knee_rom_deg",
    "peak_hip_flexion_deg",
    "peak_hip_extension_deg",
    "peak_ankle_dorsiflexion_deg",
    "peak_ankle_plantarflexion_deg",
)

OBSERVATION_METRIC_ORDER: tuple[str, ...] = (
    "peak_knee_flexion_loading_deg",
    "peak_knee_flexion_swing_deg",
    "min_knee_flexion_midstance_deg",
    "knee_rom_deg",
    "peak_hip_flexion_deg",
    "peak_hip_extension_deg",
    "peak_ankle_dorsiflexion_deg",
    "peak_ankle_plantarflexion_deg",
    "stance_pct",
    "double_support_pct",
    "walking_speed_m_s",
)


@dataclass(frozen=True)
class ReportPaths:
    """Where the report and its figures were written."""

    markdown: Path
    figures: tuple[Path, ...]


def fmt(value: float | None, digits: int = 1) -> str:
    """German number formatting with a decimal comma; ``None``/NaN becomes an en dash."""
    if value is None or not isinstance(value, int | float) or not math.isfinite(float(value)):
        return "–"
    return f"{float(value):.{digits}f}".replace(".", ",")


def _digits_for(unit: str) -> int:
    return 2 if unit in ("s", "m", "m/s") else 1


def _estimate_text(estimate: Estimate | None, unit: str) -> str:
    if estimate is None or not estimate.valid:
        return "–"
    digits = _digits_for(unit)
    return f"{fmt(estimate.mean, digits)} ± {fmt(estimate.sd, digits)} {unit} (n = {estimate.n})"


def _side_label(summary: SessionSummary, side: Side) -> str:
    if summary.operated_side is None:
        return f"Seite {side}"
    return "operierte Seite" if side == summary.operated_side else "Gegenseite"


# ------------------------------------------------------------------------------- figures
def plot_channel(
    summary: SessionSummary, channel: str, out_path: Path, *, title_note: str = ""
) -> Path | None:
    """Mean curve +- 1 SD per side against the norm band +- 1 SD; returns the written path."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    per_side = summary.curves.get(channel)
    if not per_side:
        return None

    phase = np.linspace(0.0, 100.0, 101)
    fig, ax = plt.subplots(figsize=(7.5, 4.2))

    band = summary.norm_curves.get(channel)
    if band:
        band_mean = np.asarray(band["mean_deg"], dtype=float)
        band_sd = np.asarray(band["sd_deg"], dtype=float)
        ax.fill_between(
            phase,
            band_mean - band_sd,
            band_mean + band_sd,
            color=NORM_COLOR,
            alpha=0.25,
            linewidth=0,
            label=f"Normband ± 1 SD (n = {band.get('n_subjects', '?')}, {band.get('speed_class')})",
        )
        ax.plot(phase, band_mean, color=NORM_COLOR, linewidth=1.2)

    op_side: Side = summary.operated_side or "R"
    for side in (op_side, other_side(op_side)):
        entry = per_side.get(side)
        if entry is None:
            continue
        mean = np.asarray(entry["mean_deg"], dtype=float)
        if mean.size != phase.size:
            continue
        operated = side == op_side
        color = OPERATED_COLOR if operated else CONTRA_COLOR
        style = "-" if operated else "--"
        label = f"{_side_label(summary, side)} ({side}), n = {entry.get('n_cycles', 0)} Zyklen"
        ax.plot(phase, mean, style, color=color, linewidth=2.0, label=label)
        sd = entry.get("sd_deg")
        if sd is not None:
            sd_arr = np.asarray(sd, dtype=float)
            if sd_arr.size == mean.size:
                ax.fill_between(
                    phase, mean - sd_arr, mean + sd_arr, color=color, alpha=0.15, linewidth=0
                )

    ax.axhline(0.0, color="black", linewidth=0.5)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Gangzyklus (%)")
    ax.set_ylabel("Winkel (°)")
    title = CHANNEL_LABELS_DE.get(channel, channel)
    ax.set_title(f"{title}{title_note}")
    ax.legend(loc="best", fontsize=8, framealpha=0.9)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def write_figures(
    summary: SessionSummary, out_dir: Path, *, title_note: str = ""
) -> list[tuple[str, Path]]:
    """One PNG per available angle channel; returns ``[(channel, path), ...]``."""
    written: list[tuple[str, Path]] = []
    for channel in CURVE_CHANNELS:
        path = out_dir / f"curve_{channel}.png"
        if plot_channel(summary, channel, path, title_note=title_note) is not None:
            written.append((channel, path))
    return written


# ------------------------------------------------------------------------------- sections
def _header(summary: SessionSummary, title_note: str) -> list[str]:
    meta = summary.meta
    subject = meta.get("subject", {}) or {}
    date = meta.get("date") or "ohne Datum"
    time = meta.get("time") or ""
    lines = [
        f"# Ganganalyse Session {date} {time}{title_note}".rstrip(),
        "",
        (
            "Beobachtungen aus einem Handy-Video, seitliche Ansicht, ein Durchgang je Aufnahme. "
            "Dieses Dokument ist keine Aussage über Gesundheitszustand oder Vorgehen; es zeigt "
            "gemessene Zahlen mit ihrer Streuung und ihrer Messunsicherheit "
            "(Hypothese zur Besprechung mit Fachpersonal)."
        ),
        "",
        "| Feld | Wert |",
        "| --- | --- |",
    ]
    rows: list[tuple[str, Any]] = [
        ("Datum, Uhrzeit", f"{date} {time}".strip()),
        ("Wochen nach OP", meta.get("post_op_weeks")),
        ("Operierte Seite", subject.get("operated_side") or "nicht angegeben"),
        ("Transplantat", subject.get("graft") or "nicht angegeben"),
        ("Körperhöhe", f"{fmt(subject.get('height_m'), 2)} m"),
        ("Ort", meta.get("location") or "nicht angegeben"),
        ("Schuhe", meta.get("shoes") or "nicht angegeben"),
        ("Schmerz operiertes Knie (0-10)", meta.get("pain_now_0_10")),
        ("Schmerz Gegenseite (0-10)", meta.get("pain_contra_0_10")),
        ("Müdigkeit (0-10)", meta.get("fatigue_0_10")),
        ("Schlaf (h)", meta.get("sleep_hours")),
        ("Aktivität am Vortag", meta.get("activity_yesterday") or "nicht angegeben"),
        ("Auswertung", f"{summary.pooling}, Normband-Klasse {summary.speed_class}"),
        ("Notizen", meta.get("notes") or "–"),
    ]
    for label, value in rows:
        shown = "–" if value is None or value == "" else value
        if isinstance(shown, float):
            shown = f"{int(shown)}" if float(shown).is_integer() else fmt(shown)
        lines.append(f"| {label} | {shown} |")
    lines.append("")
    pooling_text = (
        "Gepoolt wurden nur Zyklen der kameranahen Seite je Durchgang; die kamerafernen "
        "Gliedmaßen sind in der Seitenansicht teilweise verdeckt."
        if summary.pooling == "camera_near"
        else "Gepoolt wurden Zyklen beider Seiten je Durchgang (--all-sides)."
    )
    lines.extend([pooling_text, "", f"Normband-Klasse: {summary.speed_class_source}.", ""])
    return lines


def _figures_section(figures: list[tuple[str, Path]]) -> list[str]:
    if not figures:
        return ["## Mittelkurven", "", "Keine Kurven verfügbar.", ""]
    lines = [
        "## Mittelkurven gegen Normband",
        "",
        (
            "Durchgezogen: operierte Seite. Gestrichelt: Gegenseite. Grau: Normband ± 1 SD. "
            "Die farbigen Flächen sind ± 1 SD über die gepoolten Zyklen dieser Session."
        ),
        "",
    ]
    for channel, path in figures:
        label = CHANNEL_LABELS_DE.get(channel, channel)
        lines.append(f"![{label}]({path.name})")
        lines.append("")
    return lines


def _flag_text(entry: Any) -> str:
    if entry is None or entry.mdc is None:
        return "kein MDC hinterlegt"
    return "über MDC" if entry.above_mdc else "unter MDC"


def _table_section(summary: SessionSummary) -> list[str]:
    op_side: Side = summary.operated_side or "R"
    contra_side = other_side(op_side)
    op_label = _side_label(summary, op_side)
    contra_label = _side_label(summary, contra_side)
    lines = [
        "## Zeit-Weg-Parameter und diskrete Winkelwerte",
        "",
        (
            f"Mittelwert ± SD über alle gepoolten Zyklen der Session, n = Zyklen. "
            f"SI nach Robinson 1987, positiv bedeutet: {op_label} größer. Die Spalte MDC zeigt, ob "
            "der Betrag der Differenz über dem kleinsten messbaren Unterschied liegt; nur solche "
            "Zeilen sind für einen Vergleich belastbar (ADR-0003)."
        ),
        "",
        (
            f"| Kennzahl | {op_label} ({op_side}) | {contra_label} ({contra_side}) | "
            "Differenz | SI (%) | MDC | Einordnung |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name in TABLE_METRIC_ORDER:
        spec = next((m for m in METRICS if m.name == name), None)
        if spec is None:
            continue
        per_side = summary.metrics.get(name, {})
        if not per_side:
            continue
        entry = summary.symmetry.get(name)
        digits = _digits_for(spec.unit)
        delta = fmt(entry.delta, digits) if entry else "–"
        si = fmt(entry.si_operated_pct, 1) if entry else "–"
        mdc = (
            f"{fmt(entry.mdc.value, digits)} {entry.mdc.unit}"
            if entry and entry.mdc is not None
            else "–"
        )
        lines.append(
            f"| {spec.label_de} ({spec.unit}) "
            f"| {_estimate_text(per_side.get(op_side), spec.unit)} "
            f"| {_estimate_text(per_side.get(contra_side), spec.unit)} "
            f"| {delta} | {si} | {mdc} | {_flag_text(entry)} |"
        )
    lines.extend(
        [
            "",
            (
                f"Gangasymmetrie nach Plotnik (Schwungzeiten, immer ≥ 0): "
                f"{fmt(summary.gait_asymmetry_pct, 1)} % "
                "(Yogev/Plotnik et al. 2007, *Exp Brain Res* 177:336-346)."
            ),
            "",
        ]
    )
    return lines


def _observations_section(summary: SessionSummary) -> list[str]:
    op_side: Side = summary.operated_side or "R"
    op_label = _side_label(summary, op_side)
    contra_label = _side_label(summary, other_side(op_side))
    lines = [
        "## Beobachtungen",
        "",
        (
            "Jeder Satz nennt beide Seiten mit Streuung, die Differenz und den kleinsten messbaren "
            "Unterschied (MDC) mit Quelle. Liegt die Differenz unter dem MDC, ist sie von der "
            "Messunsicherheit nicht zu trennen."
        ),
        "",
    ]
    if summary.operated_side is None:
        lines.append(
            "Im meta.yaml ist keine operierte Seite angegeben; die Sätze vergleichen deshalb "
            "Seite R mit Seite L ohne weitere Zuordnung."
        )
        lines.append("")

    any_line = False
    for name in OBSERVATION_METRIC_ORDER:
        entry = summary.symmetry.get(name)
        spec = next((m for m in METRICS if m.name == name), None)
        if entry is None or spec is None:
            continue
        digits = _digits_for(spec.unit)
        unit = spec.unit
        if entry.mdc is None:
            verdict = (
                "für diese Kennzahl liegt kein MDC vor, die Differenz ist deshalb nicht "
                "gegen die Messunsicherheit einzuordnen"
            )
        else:
            relation = "über" if entry.above_mdc else "unter"
            placeholder = (
                ", Platzhalterwert bis zur eigenen Wiederholungsmessung"
                if entry.mdc.placeholder
                else ""
            )
            verdict = (
                f"Differenz {fmt(abs(entry.delta), digits)} {unit} liegt {relation} dem MDC von "
                f"{fmt(entry.mdc.value, digits)} {entry.mdc.unit} "
                f"({entry.mdc.source}{placeholder})"
            )
        lines.append(
            f"- {spec.label_de}, {op_label}: "
            f"{fmt(entry.operated.mean, digits)} ± {fmt(entry.operated.sd, digits)} {unit}, "
            f"{contra_label}: "
            f"{fmt(entry.contralateral.mean, digits)} ± {fmt(entry.contralateral.sd, digits)} "
            f"{unit}, {verdict}."
        )
        any_line = True
    if not any_line:
        lines.append("- Keine Kennzahl konnte auf beiden Seiten gebildet werden.")
    lines.extend(
        [
            "",
            (
                "Hypothese zur Besprechung mit Fachpersonal: Zeilen mit „über MDC“ sind die "
                "einzigen, die eine Nachfrage wert sind; alles darunter liegt im Rauschen dieser "
                "Messmethode."
            ),
            "",
        ]
    )
    return lines


def _norm_section(summary: SessionSummary) -> list[str]:
    lines = [
        "## Abstand zum Normband",
        "",
        (
            "Gait Variable Score (GVS) ist der RMS-Abstand der Mittelkurve zur Normband-Mittelkurve, "
            "Gait Profile Score (GPS) der RMS über die Kanäle (Baker et al. 2009, *Gait & Posture* "
            "30(3):265-269). Bei gesunden Erwachsenen liegt der GPS bei etwa 5 bis 6°. Die "
            "Normbänder stammen aus Laborsystemen mit Markern, die Videomessung misst anders; der "
            "Abstand enthält also auch einen Methodenanteil."
        ),
        "",
        "| Kanal | "
        + " | ".join(f"GVS {_side_label(summary, s)} ({s})" for s in SIDES)
        + " | "
        + " | ".join(f"außerhalb ± 2 SD ({s})" for s in SIDES)
        + " |",
        "| --- | " + " | ".join(["---"] * (2 * len(SIDES))) + " |",
    ]
    channels = sorted({c for side in SIDES for c in summary.gvs_deg.get(side, {})})
    for channel in channels:
        gvs_cells = " | ".join(
            f"{fmt(summary.gvs_deg.get(side, {}).get(channel), 1)}°" for side in SIDES
        )
        outside_cells = " | ".join(
            f"{fmt(summary.pct_outside_2sd.get(side, {}).get(channel), 0)} %" for side in SIDES
        )
        lines.append(
            f"| {CHANNEL_LABELS_DE.get(channel, channel)} | {gvs_cells} | {outside_cells} |"
        )
    gps_cells = " | ".join(f"**{fmt(summary.gps_deg.get(side), 1)}°**" for side in SIDES)
    empty = " | ".join(["–"] * len(SIDES))
    lines.append(f"| **GPS** | {gps_cells} | {empty} |")
    lines.append("")
    if summary.band_sources:
        lines.append("Normband-Quellen:")
        for key, source in sorted(summary.band_sources.items()):
            lines.append(f"- `{key}`: {source}")
        lines.append("")
    return lines


def _quality_section(summary: SessionSummary) -> list[str]:
    q = summary.quality
    n_cycles = q.get("n_cycles", {})
    dropped = q.get("n_dropped_cycles", {})
    nan_pct = q.get("mean_nan_pct", {})
    lines = [
        "## Qualität",
        "",
        f"- Durchgänge: {q.get('n_passes_ok', 0)} von {q.get('n_passes_total', 0)} ausgewertet.",
    ]
    failed = q.get("failed_passes") or {}
    for name, error in failed.items():
        lines.append(f"  - {name}: nicht ausgewertet ({error})")
    for side in SIDES:
        lines.append(
            f"- Zyklen Seite {side} ({_side_label(summary, side)}): {n_cycles.get(side, 0)} "
            f"gepoolt, {dropped.get(side, 0)} als Ausreißer verworfen, "
            f"fehlende Samples im Mittel {fmt(nan_pct.get(side), 1)} %."
        )
    fps = q.get("fps") or []
    fps_text = ", ".join(fmt(f, 1) for f in fps) if fps else "–"
    lines.append(f"- Bildrate der ausgewerteten Videos: {fps_text} fps.")
    meta_fps = q.get("fps_meta_camera_a")
    if meta_fps:
        lines.append(f"- Im meta.yaml notierte Bildrate Kamera A: {fmt(meta_fps, 0)} fps.")
    camera_b = q.get("camera_b_passes") or []
    if camera_b:
        lines.append(
            f"- Kamera B: {len(camera_b)} Durchgänge vorhanden, in dieser Auswertung nicht "
            "verarbeitet."
        )
    cycles_per_pass = q.get("cycles_per_pass", {})
    for side in SIDES:
        detail = cycles_per_pass.get(side) or {}
        if detail:
            joined = ", ".join(f"{name}: {count}" for name, count in detail.items())
            lines.append(f"- Zyklen je Durchgang, Seite {side}: {joined}.")
    if summary.warnings:
        lines.append("- Hinweise aus der Verarbeitung:")
        for warning in summary.warnings:
            lines.append(f"  - {warning}")
    lines.append("")
    return lines


def render_markdown(
    summary: SessionSummary, figures: list[tuple[str, Path]], *, title_note: str = ""
) -> str:
    """Assemble the whole report; ``title_note`` is appended to the title and figure titles."""
    parts: list[str] = []
    parts.extend(_header(summary, title_note))
    parts.extend(_figures_section(figures))
    parts.extend(_table_section(summary))
    parts.extend(_observations_section(summary))
    parts.extend(_norm_section(summary))
    parts.extend(["## Was dieses Video nicht sieht", "", NOT_VISIBLE_TEXT, ""])
    parts.extend(_quality_section(summary))
    parts.extend(
        [
            "---",
            "",
            (
                f"Erstellt von OpenACL am {summary.generated_utc} aus "
                f"`{summary.session_dir}`. Rohzahlen: `session.json`."
            ),
            "",
        ]
    )
    return "\n".join(parts)


def write_report(
    summary: SessionSummary, out_dir: Path | str, *, title_note: str = ""
) -> ReportPaths:
    """Write ``report.md`` and its PNGs into ``out_dir``."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    figures = write_figures(summary, out_dir, title_note=title_note)
    text = render_markdown(summary, figures, title_note=title_note)
    markdown = out_dir / REPORT_NAME
    markdown.write_text(text, encoding="utf-8")
    return ReportPaths(markdown=markdown, figures=tuple(path for _, path in figures))

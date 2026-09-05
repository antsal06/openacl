"""Synthetic Apple Health export in the real (Apple-Health-Export-Version 14) XML layout.

Values are entirely made up -- no real health data anywhere in this repository (CLAUDE.md).
Deliberately exercises both unit variants seen in the wild (``km/hr`` vs ``m/s`` for walking
speed, ``cm`` vs ``m`` for step length) and mixed UTC offsets (``+0100``/``+0200``, i.e. a
daylight-saving transition) so the parser's unit and timezone handling are actually tested.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import quoteattr
from zipfile import ZIP_DEFLATED, ZipFile

_HEADER = '<?xml version="1.0" encoding="UTF-8"?>\n<HealthData locale="de_AT">\n'
_FOOTER = "</HealthData>\n"

_DEVICE = (
    "<<HKDevice: 0x1>, name:iPhone, manufacturer:Apple Inc., model:iPhone, "
    "hardware:iPhone13,2, software:18.5, creation date:2025-06-12 21:50:16 +0000>"
)


@dataclass(frozen=True)
class SyntheticRecord:
    hk_type: str
    unit: str
    value: str
    start: str  # "YYYY-MM-DD HH:MM:SS +ZZZZ"
    end: str
    source_name: str = "iPhone von Anton"
    device: str | None = _DEVICE


def _record_xml(rec: SyntheticRecord) -> str:
    device_attr = f" device={quoteattr(rec.device)}" if rec.device is not None else ""
    return (
        f"<Record type={quoteattr(rec.hk_type)} sourceName={quoteattr(rec.source_name)} "
        f'sourceVersion="18.5"{device_attr} unit={quoteattr(rec.unit)} '
        f"creationDate={quoteattr(rec.end)} startDate={quoteattr(rec.start)} "
        f"endDate={quoteattr(rec.end)} value={quoteattr(rec.value)}/>\n"
    )


def default_records() -> list[SyntheticRecord]:
    """~40 made-up records spanning all six gait/activity types, both unit variants per
    quantity that has one, and a +0100 -> +0200 (CET -> CEST) offset change partway through."""
    records: list[SyntheticRecord] = []

    # WalkingSpeed: km/hr (the common real-world unit) then m/s, across the DST boundary.
    speed_kmh = [3.6, 4.32, 5.04, 3.24, 4.68, 3.96, 4.5, 3.78]
    for i, kmh in enumerate(speed_kmh):
        offset = "+0100" if i < 4 else "+0200"
        day = f"2026-0{2 if i < 4 else 3}-{10 + i:02d}"
        records.append(
            SyntheticRecord(
                "HKQuantityTypeIdentifierWalkingSpeed",
                "km/hr",
                str(kmh),
                f"{day} 08:00:00 {offset}",
                f"{day} 08:00:05 {offset}",
            )
        )
    records.append(
        SyntheticRecord(
            "HKQuantityTypeIdentifierWalkingSpeed",
            "m/s",
            "1.1",
            "2026-04-01 09:00:00 +0200",
            "2026-04-01 09:00:05 +0200",
        )
    )

    # WalkingStepLength: cm then m.
    step_cm = [60, 65, 58, 70, 62, 55, 68, 63]
    for i, cm in enumerate(step_cm):
        day = f"2026-02-{10 + i:02d}"
        records.append(
            SyntheticRecord(
                "HKQuantityTypeIdentifierWalkingStepLength",
                "cm",
                str(cm),
                f"{day} 08:00:00 +0100",
                f"{day} 08:00:05 +0100",
            )
        )
    records.append(
        SyntheticRecord(
            "HKQuantityTypeIdentifierWalkingStepLength",
            "m",
            "0.66",
            "2026-03-15 09:00:00 +0100",
            "2026-03-15 09:00:05 +0100",
        )
    )

    # WalkingDoubleSupportPercentage: HealthKit fraction (0-1) despite unit="%".
    dsp = [0.20, 0.22, 0.19, 0.25, 0.21, 0.23, 0.18, 0.24]
    for i, frac in enumerate(dsp):
        day = f"2026-02-{10 + i:02d}"
        records.append(
            SyntheticRecord(
                "HKQuantityTypeIdentifierWalkingDoubleSupportPercentage",
                "%",
                str(frac),
                f"{day} 08:00:00 +0100",
                f"{day} 08:00:05 +0100",
            )
        )

    # WalkingAsymmetryPercentage: fraction (0-1).
    asym = [0.02, 0.03, 0.01, 0.04, 0.0, 0.05]
    for i, frac in enumerate(asym):
        day = f"2026-02-{10 + i:02d}"
        records.append(
            SyntheticRecord(
                "HKQuantityTypeIdentifierWalkingAsymmetryPercentage",
                "%",
                str(frac),
                f"{day} 08:00:00 +0100",
                f"{day} 08:00:05 +0100",
            )
        )

    # AppleWalkingSteadiness: fraction (0-1), sparse (Apple emits this weekly).
    for i, frac in enumerate([0.95, 0.9, 0.85]):
        day = f"2026-02-{10 + i * 7:02d}"
        records.append(
            SyntheticRecord(
                "HKQuantityTypeIdentifierAppleWalkingSteadiness",
                "%",
                str(frac),
                f"{day} 02:00:00 +0100",
                f"{day} 02:00:05 +0100",
            )
        )

    # StepCount: activity context, unrelated unit ("count").
    for i, n in enumerate([50, 120, 80]):
        day = f"2026-02-{10 + i:02d}"
        records.append(
            SyntheticRecord(
                "HKQuantityTypeIdentifierStepCount",
                "count",
                str(n),
                f"{day} 08:00:00 +0100",
                f"{day} 08:05:00 +0100",
            )
        )

    # A non-gait record type that must be ignored entirely.
    records.append(
        SyntheticRecord(
            "HKQuantityTypeIdentifierHeartRate",
            "count/min",
            "70",
            "2026-02-10 08:00:00 +0100",
            "2026-02-10 08:00:00 +0100",
            device=None,
        )
    )

    return records


def write_export_xml(path: Path, records: list[SyntheticRecord] | None = None) -> Path:
    """Write a synthetic ``export.xml`` (Apple Health export XML layout) to ``path``."""
    records = default_records() if records is None else records
    body = "".join(_record_xml(r) for r in records)
    path.write_text(_HEADER + body + _FOOTER, encoding="utf-8")
    return path


def write_export_zip(path: Path, records: list[SyntheticRecord] | None = None) -> Path:
    """Write a synthetic ``export.zip`` with ``apple_health_export/export.xml`` inside,
    matching the real Apple Health export archive layout (plus a decoy ``export_cda.xml``)."""
    records = default_records() if records is None else records
    body = "".join(_record_xml(r) for r in records)
    xml_text = _HEADER + body + _FOOTER
    with ZipFile(path, "w", ZIP_DEFLATED) as zf:
        zf.writestr("apple_health_export/export.xml", xml_text)
        zf.writestr("apple_health_export/export_cda.xml", "<HealthData/>")
    return path

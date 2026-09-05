"""Streaming parser for Apple Health exports, restricted to gait-relevant records.

Reads ``export.xml`` (directly, or from inside the zipped export Apple hands out) with
``xml.etree.ElementTree.iterparse`` so the ~90 MB / ~120k-record file never has to sit fully
in memory as a DOM. Only ``Record`` elements of the walking-gait quantity types are kept;
everything else (workouts, correlations, clinical records, ...) is dropped as it streams past.

Record types read (``HKQuantityTypeIdentifier<X>`` -> output ``metric``)::

    WalkingSpeed                     -> walking_speed_m_s
    WalkingStepLength                -> step_length_m
    WalkingDoubleSupportPercentage   -> double_support_pct
    WalkingAsymmetryPercentage       -> walking_asymmetry_pct
    AppleWalkingSteadiness           -> walking_steadiness_pct
    StepCount                        -> step_count            (activity context only)

Unit handling
-------------
Apple's export uses whatever unit HealthKit stored the sample in, which for these types has
been observed to vary by device/OS version. ``WalkingSpeed`` is converted from ``km/hr`` to
``m/s`` (divide by 3.6); ``m/s`` is passed through. ``WalkingStepLength`` is converted from
``cm`` to ``m`` (divide by 100); ``m`` is passed through.

The three ``*Percentage``/steadiness quantities carry ``unit="%"`` in the XML, but HealthKit's
``HKUnit.percent()`` stores the *fraction* (0-1), not the percent number -- e.g. a double-support
value of ``0.283`` means 28.3 %, confirmed against this project's own export. This loader
multiplies by 100 so ``value`` is on an actual 0-100 percent scale, matching the ``_pct`` suffix
in the metric name (openacl convention: every number carries its unit in the name).

Any unit not covered above raises ``ValueError`` rather than silently mis-scaling a health
measurement.

Time zones
----------
``startDate``/``endDate`` are local wall-clock time with a fixed UTC offset, e.g.
``"2026-08-05 08:35:38 +0200"``. Each is parsed with its own offset (``%z``) and converted to
UTC immediately, so the returned ``start``/``end`` columns are unambiguous, sortable instants
(``datetime64[ns, UTC]``) regardless of how many DST transitions the export spans. Converting
back to local calendar dates/weeks for aggregation is the job of :mod:`openacl.health.daily`.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Final

import pandas as pd

#: HealthKit type identifier suffix -> canonical, SI-named metric column value.
GAIT_RECORD_TYPES: Final[dict[str, str]] = {
    "HKQuantityTypeIdentifierWalkingSpeed": "walking_speed_m_s",
    "HKQuantityTypeIdentifierWalkingStepLength": "step_length_m",
    "HKQuantityTypeIdentifierWalkingDoubleSupportPercentage": "double_support_pct",
    "HKQuantityTypeIdentifierWalkingAsymmetryPercentage": "walking_asymmetry_pct",
    "HKQuantityTypeIdentifierAppleWalkingSteadiness": "walking_steadiness_pct",
    "HKQuantityTypeIdentifierStepCount": "step_count",
}

#: Output columns of :func:`load_gait_export`, in order.
EXPORT_COLUMNS: Final[tuple[str, ...]] = (
    "metric",
    "start",
    "end",
    "value",
    "unit",
    "source_name",
    "device",
)

_PERCENT_METRICS: Final[frozenset[str]] = frozenset(
    {"double_support_pct", "walking_asymmetry_pct", "walking_steadiness_pct"}
)

#: Field values may contain embedded commas (e.g. hardware id ``"iPhone13,2"``); the field
#: separator in the device string is always a comma *followed by whitespace*, so a bare comma
#: not followed by whitespace is treated as part of the value, not a separator.
_DEVICE_FIELD_RE = re.compile(r"(?:^|,\s+)(name|model|hardware):((?:[^,>]|,(?!\s))*)")


def _convert(metric: str, raw_value: float, raw_unit: str) -> tuple[float, str]:
    """Convert one raw HealthKit ``(value, unit)`` pair to the metric's SI/target unit.

    Raises ``ValueError`` for a unit this loader does not know how to convert, so an
    unexpected export format fails loudly instead of silently producing a wrong scale.
    """
    if metric == "walking_speed_m_s":
        if raw_unit in ("km/hr", "km/h"):
            return raw_value / 3.6, "m/s"
        if raw_unit == "m/s":
            return raw_value, "m/s"
        raise ValueError(f"unexpected unit {raw_unit!r} for {metric}")
    if metric == "step_length_m":
        if raw_unit == "cm":
            return raw_value / 100.0, "m"
        if raw_unit == "m":
            return raw_value, "m"
        raise ValueError(f"unexpected unit {raw_unit!r} for {metric}")
    if metric in _PERCENT_METRICS:
        if raw_unit == "%":
            return raw_value * 100.0, "pct"
        raise ValueError(f"unexpected unit {raw_unit!r} for {metric}")
    if metric == "step_count":
        if raw_unit == "count":
            return raw_value, "count"
        raise ValueError(f"unexpected unit {raw_unit!r} for {metric}")
    raise ValueError(f"no conversion rule for metric {metric!r}")  # pragma: no cover - defensive


def _parse_apple_datetime(value: str) -> pd.Timestamp:
    """Parse an Apple Health ``"YYYY-MM-DD HH:MM:SS +ZZZZ"`` timestamp to a UTC ``Timestamp``."""
    ts = pd.Timestamp(value)  # pandas parses the "%Y-%m-%d %H:%M:%S %z" format directly
    return ts.tz_convert("UTC")


def _summarize_device(raw: str | None) -> str:
    """Extract a short ``"<model> (<hardware>)"`` label from the verbose ``device`` attribute.

    The raw attribute looks like
    ``"<<HKDevice: 0x...>, name:iPhone, manufacturer:Apple Inc., model:iPhone, ...>"``.
    Returns ``""`` if ``raw`` is missing or unparsable.
    """
    if not raw:
        return ""
    fields = dict(_DEVICE_FIELD_RE.findall(raw))
    name = fields.get("model") or fields.get("name")
    if name is None:
        return ""
    hardware = fields.get("hardware")
    return f"{name.strip()} ({hardware.strip()})" if hardware else name.strip()


def _find_export_xml_member(zf: zipfile.ZipFile) -> str:
    """Locate the ``export.xml`` entry inside an Apple Health export zip.

    Excludes ``export_cda.xml`` (the separate clinical-document export Apple also includes).
    """
    candidates = [
        name
        for name in zf.namelist()
        if name.endswith("export.xml") and not name.endswith("export_cda.xml")
    ]
    if not candidates:
        raise FileNotFoundError("no export.xml entry found in zip")
    candidates.sort(key=len)  # prefer the shortest path, e.g. "apple_health_export/export.xml"
    return candidates[0]


@contextmanager
def _open_xml_source(path: Path) -> Iterator[BinaryIO]:
    """Yield a binary file object for ``export.xml``, transparently unzipping if needed."""
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf, zf.open(_find_export_xml_member(zf)) as fh:
            yield fh
    else:
        with open(path, "rb") as fh:
            yield fh


def _record_to_row(elem: ET.Element, metric: str) -> dict[str, object]:
    raw_unit = elem.get("unit") or ""
    raw_value = float(elem.get("value", "nan"))
    value, unit = _convert(metric, raw_value, raw_unit)
    return {
        "metric": metric,
        "start": _parse_apple_datetime(elem.get("startDate", "")),
        "end": _parse_apple_datetime(elem.get("endDate", "")),
        "value": value,
        "unit": unit,
        "source_name": elem.get("sourceName") or "",
        "device": _summarize_device(elem.get("device")),
    }


def iter_gait_rows(source: Path) -> Iterator[dict[str, object]]:
    """Stream gait-relevant ``Record`` rows out of an Apple Health export.

    Uses ``iterparse`` and clears each finished element (and the root's already-processed
    children) as it goes, so peak memory stays close to the size of one XML subtree rather
    than the whole document -- required for the ~90 MB / ~120k-record real export.
    """
    with _open_xml_source(source) as fh:
        context = ET.iterparse(fh, events=("start", "end"))
        _, root = next(context)  # root start event: keep a handle so we can free its children
        for event, elem in context:
            if event != "end" or elem.tag != "Record":
                continue
            metric = GAIT_RECORD_TYPES.get(elem.get("type", ""))
            if metric is not None:
                yield _record_to_row(elem, metric)
            elem.clear()
            root.clear()  # drop references to already-processed siblings/descendants


def load_gait_export(source: str | Path) -> pd.DataFrame:
    """Parse an Apple Health export (``export.xml`` or ``export.zip``) into a gait DataFrame.

    Returns a ``pandas.DataFrame`` with columns ``metric, start, end, value, unit, source_name,
    device`` (see :data:`EXPORT_COLUMNS`), sorted by ``metric`` then ``start``. ``start``/``end``
    are timezone-aware (UTC). Empty input yields an empty, correctly-typed DataFrame.
    """
    path = Path(source)
    rows = list(iter_gait_rows(path))
    df = pd.DataFrame(rows, columns=list(EXPORT_COLUMNS))
    if df.empty:
        df["start"] = pd.to_datetime(df["start"], utc=True)
        df["end"] = pd.to_datetime(df["end"], utc=True)
        return df
    df["start"] = pd.to_datetime(df["start"], utc=True)
    df["end"] = pd.to_datetime(df["end"], utc=True)
    df["value"] = df["value"].astype(float)
    return df.sort_values(["metric", "start"], kind="stable").reset_index(drop=True)

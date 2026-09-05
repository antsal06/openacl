"""Command line entry point: ``python -m openacl.health <export.zip|export.xml> --out DIR``.

Parses an Apple Health export, aggregates the walking-gait metrics per day/week, compares
ACLR recovery periods against ``--surgery-date`` (if given), and writes three files into
``--out``: ``health_daily.parquet`` (daily stats + 7-day rolling median), ``health_summary.json``
(period comparison and the double-support measurement-quality note) and ``health_trends.png``
(the 4-panel trend figure). Not wired into ``openacl.cli`` yet -- run as a module.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from .daily import period_summary_json, rolling_median_7d
from .export import load_gait_export
from .plot import plot_trends

logger = logging.getLogger(__name__)


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got {value!r}") from exc


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m openacl.health",
        description="Apple-Health-Export in Gangmetriken-Tages-/Wochenwerte und Periodenvergleich.",
    )
    parser.add_argument("source", type=Path, help="export.zip oder export.xml")
    parser.add_argument("--out", type=Path, required=True, help="Ausgabeverzeichnis")
    parser.add_argument(
        "--surgery-date",
        type=_parse_date,
        default=None,
        help="OP-Datum (YYYY-MM-DD); ohne Angabe entfällt der Periodenvergleich und die "
        "OP-Linie/Schattierung im Plot",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = build_arg_parser().parse_args(argv)

    if not args.source.exists():
        logger.error("Quelle nicht gefunden: %s", args.source)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)

    logger.info("Lese %s ...", args.source)
    df = load_gait_export(args.source)
    if df.empty:
        logger.warning("Keine Gangmetrik-Records gefunden.")

    daily = rolling_median_7d(df)
    daily_path = args.out / "health_daily.parquet"
    daily.to_parquet(daily_path, index=False)

    if args.surgery_date is not None:
        summary = period_summary_json(df, args.surgery_date)
    else:
        summary = {
            "surgery_date": None,
            "note": "kein --surgery-date angegeben, kein Periodenvergleich berechnet",
            "n_records": len(df),
        }
    summary_path = args.out / "health_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    png_path = args.out / "health_trends.png"
    plot_trends(daily, png_path, surgery_date=args.surgery_date)

    for path in (daily_path, summary_path, png_path):
        logger.info("geschrieben: %s", path)

    if not df.empty:
        counts = df.groupby("metric")["value"].count().to_dict()
        logger.info("Records je Metrik: %s", counts)
        logger.info(
            "Zeitraum: %s bis %s (UTC)", df["start"].min().isoformat(), df["end"].max().isoformat()
        )
        sources = sorted((set(df["source_name"]) | set(df["device"])) - {""})
        logger.info("Quellen/Geräte: %s", sources)

    return 0


if __name__ == "__main__":
    sys.exit(main())

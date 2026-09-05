#!/usr/bin/env python3
"""Download public reference gait datasets into ``data/norm/<dataset>/`` (gitignored).

Idempotent: a file whose size already matches the figshare record is skipped.
Sizes are printed before anything is transferred, so a download can be aborted early.

Only the *processed* files are fetched by default. The raw C3D archives of Fukuchi
(1.5 GB) and Van Criekinge (6.2 GB MAT / 0.5 GB C3D) are not needed for norm bands
and are therefore excluded; ``--include-raw`` pulls them anyway.

Usage
-----
    python scripts/download_normdata.py --list
    python scripts/download_normdata.py --dataset fukuchi2018
    python scripts/download_normdata.py --dataset all
"""

from __future__ import annotations

import argparse
import dataclasses
import shutil
import sys
import time
import zipfile
from pathlib import Path

import requests

FIGSHARE_API = "https://api.figshare.com/v2/articles/{article_id}"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEST = REPO_ROOT / "data" / "norm"
CHUNK_BYTES = 1 << 20


@dataclasses.dataclass(frozen=True)
class DatasetSpec:
    """One public dataset and the figshare files we actually need."""

    key: str
    citation: str
    license_name: str
    license_url: str
    articles: tuple[int, ...]
    """Figshare article ids that hold the processed files."""

    raw_articles: tuple[int, ...] = ()
    """Article ids holding raw C3D/MAT; only fetched with ``--include-raw``."""

    keep_names: tuple[str, ...] = ()
    """If non-empty, only files whose name is listed here are downloaded."""

    unzip_patterns: tuple[str, ...] = ()
    """Glob patterns extracted from every downloaded ``.zip`` into ``<dest>/ascii/``."""


DATASETS: dict[str, DatasetSpec] = {
    "fukuchi2018": DatasetSpec(
        key="fukuchi2018",
        citation=(
            "Fukuchi CA, Fukuchi RK, Duarte M (2018). A public data set of overground and "
            "treadmill walking kinematics and kinetics of healthy individuals. PeerJ 6:e4640. "
            "doi:10.6084/m9.figshare.5722711"
        ),
        license_name="CC BY 4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        articles=(5722711,),
        keep_names=("WBDSascii.zip", "WBDSinfo.xlsx"),
        unzip_patterns=("*ang.txt", "*grf.txt"),
    ),
    "schreiber2019": DatasetSpec(
        key="schreiber2019",
        citation=(
            "Schreiber C, Moissenet F (2019). A multimodal dataset of human gait at different "
            "walking speeds established on injury-free adult participants. Sci Data 6:111. "
            "doi:10.6084/m9.figshare.7734767"
        ),
        license_name="CC BY 4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        articles=(7734767,),
    ),
    "vancriekinge2023": DatasetSpec(
        key="vancriekinge2023",
        citation=(
            "Van Criekinge T, Saeys W, Truijen S, et al. (2023). A full-body motion capture gait "
            "dataset of 138 able-bodied adults across the life span and 50 stroke survivors. "
            "Sci Data 10:852. doi:10.6084/m9.figshare.c.6503791"
        ),
        license_name="CC0 1.0",
        license_url="https://creativecommons.org/publicdomain/zero/1.0/",
        articles=(24192489,),  # post-processed Excel, able-bodied adults, 38 MB
        raw_articles=(24192480,),  # C3D of the 138 able-bodied adults, 463 MB
    ),
}


def _fmt_size(n_bytes: int) -> str:
    """Human readable byte count."""
    mb = n_bytes / 1e6
    return f"{mb / 1000:.2f} GB" if mb >= 1000 else f"{mb:.1f} MB"


def fetch_article(article_id: int, session: requests.Session, attempts: int = 4) -> dict:
    """Return the figshare article record (metadata plus file list).

    The figshare API is occasionally unreachable for a few seconds, so connection errors are
    retried with a short backoff before the call is given up on.
    """
    for attempt in range(1, attempts + 1):
        try:
            response = session.get(FIGSHARE_API.format(article_id=article_id), timeout=(15, 60))
            response.raise_for_status()
            return response.json()
        except (requests.ConnectionError, requests.Timeout):
            if attempt == attempts:
                raise
            print(f"  figshare API unreachable, retry {attempt}/{attempts - 1}")
            time.sleep(2 * attempt)
    raise RuntimeError("unreachable")


def _wanted_files(spec: DatasetSpec, article: dict) -> list[dict]:
    files = article.get("files", [])
    if spec.keep_names:
        files = [f for f in files if f["name"] in spec.keep_names]
    # figshare keeps superseded uploads under the same name; keep the newest id only.
    newest: dict[str, dict] = {}
    for f in files:
        if f["name"] not in newest or f["id"] > newest[f["name"]]["id"]:
            newest[f["name"]] = f
    return sorted(newest.values(), key=lambda f: f["name"])


def plan(spec: DatasetSpec, session: requests.Session, include_raw: bool) -> list[dict]:
    """Resolve the figshare file records this dataset needs, newest version each."""
    article_ids = spec.articles + (spec.raw_articles if include_raw else ())
    files: list[dict] = []
    for article_id in article_ids:
        article = fetch_article(article_id, session)
        got = _wanted_files(spec, article)
        for f in got:
            f["_license"] = article.get("license", {}).get("name", "unknown")
        files.extend(got)
    return files


def download_file(record: dict, dest: Path, session: requests.Session) -> bool:
    """Download one figshare file. Returns ``True`` if bytes were transferred."""
    target = dest / record["name"]
    if target.exists() and target.stat().st_size == record["size"]:
        print(f"  skip (already complete) {record['name']}")
        return False
    tmp = target.with_suffix(target.suffix + ".part")
    url = record.get("download_url") or f"https://ndownloader.figshare.com/files/{record['id']}"
    print(f"  get  {record['name']} ({_fmt_size(record['size'])})")
    with session.get(url, stream=True, timeout=(30, 600)) as response:
        response.raise_for_status()
        with tmp.open("wb") as fh:
            for chunk in response.iter_content(CHUNK_BYTES):
                fh.write(chunk)
    tmp.replace(target)
    return True


def extract(spec: DatasetSpec, dest: Path) -> None:
    """Extract the patterns the loaders need from every downloaded archive."""
    if not spec.unzip_patterns:
        return
    out_dir = dest / "ascii"
    out_dir.mkdir(parents=True, exist_ok=True)
    for archive in sorted(dest.glob("*.zip")):
        with zipfile.ZipFile(archive) as zf:
            names = [
                n
                for n in zf.namelist()
                if any(Path(n).match(p) for p in spec.unzip_patterns) and not n.endswith("/")
            ]
            new = [n for n in names if not (out_dir / Path(n).name).exists()]
            if not new:
                print(f"  skip (already extracted) {archive.name}: {len(names)} files")
                continue
            print(f"  unzip {archive.name}: {len(new)} of {len(names)} files -> {out_dir}")
            for name in new:
                with zf.open(name) as src, (out_dir / Path(name).name).open("wb") as dst:
                    shutil.copyfileobj(src, dst)


def run(keys: list[str], dest_root: Path, include_raw: bool, list_only: bool) -> int:
    """Download (or just list) the requested datasets."""
    session = requests.Session()
    session.headers["User-Agent"] = "openacl-normdata/1.0"
    total = 0
    plans: dict[str, list[dict]] = {}
    for key in keys:
        spec = DATASETS[key]
        files = plan(spec, session, include_raw)
        plans[key] = files
        size = sum(f["size"] for f in files)
        total += size
        print(f"\n{key}  [{spec.license_name}]  {_fmt_size(size)}")
        print(f"  {spec.citation}")
        for f in files:
            print(f"    - {f['name']:<60s} {_fmt_size(f['size']):>10s}  ({f['_license']})")
    print(f"\ntotal to consider: {_fmt_size(total)}")
    if list_only:
        return 0

    for key in keys:
        spec = DATASETS[key]
        dest = dest_root / key
        dest.mkdir(parents=True, exist_ok=True)
        print(f"\n== {key} -> {dest}")
        (dest / "LICENSE.txt").write_text(
            f"{spec.citation}\n\nLicense: {spec.license_name}\n{spec.license_url}\n",
            encoding="utf-8",
        )
        for record in plans[key]:
            download_file(record, dest, session)
        extract(spec, dest)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        default="fukuchi2018",
        choices=[*DATASETS, "all"],
        help="which dataset to fetch (default: fukuchi2018)",
    )
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument(
        "--include-raw", action="store_true", help="also fetch the raw C3D/MAT archives"
    )
    parser.add_argument("--list", action="store_true", help="only print sizes and licenses")
    args = parser.parse_args(argv)
    keys = list(DATASETS) if args.dataset == "all" else [args.dataset]
    return run(keys, args.dest, args.include_raw, args.list)


if __name__ == "__main__":
    sys.exit(main())

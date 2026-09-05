#!/usr/bin/env python3
"""Render the norm bands to ``docs/img/normbands_v1.png`` for a quick visual check.

Usage::

    python scripts/plot_normbands.py                 # from the shipped parquet
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from openacl.norm import bands as nb

CHANNELS = ("hip_flexion_deg", "knee_flexion_deg", "ankle_dorsiflexion_deg")
CLASS_STYLE = {
    "slow": ("#4C72B0", "-"),
    "comfortable": ("#55A868", "-"),
    "fast": ("#C44E52", "-"),
    "preferred": ("#8172B2", "--"),
}
CLASS_ORDER = ("slow", "comfortable", "fast", "preferred")


def plot_bands(bands: pd.DataFrame, out_path: Path) -> Path:
    """Draw mean +/- 1 SD per channel and speed class into one PNG."""
    curves = bands[bands["kind"] == "angle_curve"]
    fig, axes = plt.subplots(1, len(CHANNELS), figsize=(13, 4.4), sharex=True)
    present = [c for c in CLASS_ORDER if c in set(curves["speed_class"])]
    for ax, channel in zip(axes, CHANNELS, strict=True):
        part = curves[curves["channel"] == channel]
        for speed_class in present:
            group = part[part["speed_class"] == speed_class].sort_values("pct")
            if group.empty:
                continue
            colour, style = CLASS_STYLE.get(speed_class, ("#888888", ":"))
            pct = group["pct"].to_numpy()
            mean = group["mean"].to_numpy()
            sd = group["sd"].to_numpy()
            n = int(group["n_subjects"].max())
            ax.fill_between(pct, mean - sd, mean + sd, color=colour, alpha=0.16, linewidth=0)
            ax.plot(pct, mean, style, color=colour, lw=1.8, label=f"{speed_class} (n={n})")
        ax.axhline(0, color="0.6", lw=0.7)
        ax.set_title(channel.replace("_deg", "").replace("_", " "), fontsize=11)
        ax.set_xlabel("Gangzyklus [%]")
        ax.set_xlim(0, 100)
        ax.grid(alpha=0.25, lw=0.5)
    axes[0].set_ylabel("Winkel [deg]")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, fontsize=9, ncol=len(labels), loc="lower center", frameon=False)
    fig.suptitle(
        "OpenACL Normbänder v1 — Mittelwert ± 1 SD, L/R gepoolt "
        "(Fukuchi 2018 overground, CC BY 4.0; Van Criekinge 2023 CC0)",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "docs" / "img" / "normbands_v1.png")
    args = parser.parse_args(argv)
    plot_bands(nb.read_normband_table(), args.out)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Command line entry point: ``openacl analyze <video>`` and ``openacl probe <video>``."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from openacl.schema import KinematicsResult, Side

logger = logging.getLogger(__name__)

_ANGLE_PANELS: tuple[tuple[str, str], ...] = (
    ("knee_flexion_deg", "Knee flexion"),
    ("hip_flexion_deg", "Hip flexion"),
    ("ankle_dorsiflexion_deg", "Ankle dorsiflexion"),
)


def _default_out_dir(video: Path) -> Path:
    return Path.cwd() / f"{video.stem}_openacl_out"


def _plot_angles(result: KinematicsResult, out_path: Path) -> None:
    """Write ``angles.png``: knee/hip/ankle flexion, left and right, over time."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(len(_ANGLE_PANELS), 1, sharex=True, figsize=(9, 8))
    for ax, (base_name, title) in zip(axes, _ANGLE_PANELS, strict=True):
        any_plotted = False
        for side, color in (("L", "tab:blue"), ("R", "tab:red")):
            key = f"{base_name}_{side}"
            if key in result.angles_deg:
                ax.plot(result.time_s, result.angles_deg[key], label=side, color=color)
                any_plotted = True
        ax.set_ylabel("deg")
        ax.set_title(title)
        ax.axhline(0.0, color="gray", linewidth=0.5)
        if any_plotted:
            ax.legend(loc="upper right")
    axes[-1].set_xlabel("time (s)")
    fig.suptitle(f"{result.backend} kinematics ({Path(result.meta.get('video', '')).name})")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def _cmd_analyze(args: argparse.Namespace) -> int:
    from openacl.backends.sports2d import run_sports2d

    video = Path(args.video)
    if not video.exists():
        print(f"error: video not found: {video}", file=sys.stderr)
        return 1

    out_dir = Path(args.out) if args.out else _default_out_dir(video)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Running sports2d ({args.mode}) on {video} -> {out_dir}")
    result = run_sports2d(
        video,
        out_dir,
        mode=args.mode,
        person_height_m=args.height_m,
        visible_side=args.side,
    )
    print(
        f"Kinematics saved to {out_dir / 'kinematics.npz'} / "
        f"{out_dir / 'kinematics.json'} ({result.n_frames} frames @ {result.fps:.1f} fps)"
    )

    angles_path = out_dir / "angles.png"
    _plot_angles(result, angles_path)
    print(f"Angle overview saved to {angles_path}")

    operated_side: Side | None = args.operated_side
    try:
        from openacl.core.pipeline import analyze
    except ImportError:
        print("openacl.core.pipeline not available yet; kinematics only.")
        return 0

    normbands = None
    try:
        from openacl.norm import load_normbands

        normbands = load_normbands()
    except Exception as exc:  # noqa: BLE001 - norm bands are optional at this stage
        print(f"norm bands not loaded ({exc}); deviation scores skipped.")

    # Speed class defaults to "comfortable" until walking speed is measurable (needs a scale).
    analysis = analyze(
        result, operated_side=operated_side, normbands=normbands, speed_class=args.speed_class
    )
    n_valid = analysis.n_valid_cycles
    speed = analysis.spatiotemporal.both.walking_speed_m_s
    summary = f"Gait-core summary: valid cycles L={n_valid.get('L', 0)} R={n_valid.get('R', 0)}"
    if speed is not None:
        summary += f", speed={speed.mean:.2f} m/s"
    print(summary)
    if analysis.deviation is not None:
        gps = analysis.deviation.gps_deg
        print(
            f"Gait Profile Score vs norm band ({args.speed_class}): "
            f"L={gps.get('L', float('nan')):.1f} deg, R={gps.get('R', float('nan')):.1f} deg"
        )
    if analysis.warnings:
        print("Warnings:")
        for warning in analysis.warnings:
            print(f"  - {warning}")
    return 0


def _cmd_probe(args: argparse.Namespace) -> int:
    from openacl.backends.video import probe

    video = Path(args.video)
    if not video.exists():
        print(f"error: video not found: {video}", file=sys.stderr)
        return 1

    info = probe(video)
    print(f"path:       {info.path}")
    print(f"fps:        {info.fps:.3f}")
    print(f"resolution: {info.width}x{info.height}")
    print(f"n_frames:   {info.n_frames}")
    print(f"duration_s: {info.duration_s:.3f}")
    print(f"codec:      {info.codec}")
    if info.warnings:
        print("warnings:")
        for warning in info.warnings:
            print(f"  - {warning}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="openacl", description="Smartphone-video gait analysis.")
    parser.add_argument("--version", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    analyze_parser = subparsers.add_parser(
        "analyze", help="Run kinematics (+ gait-core) on a video."
    )
    analyze_parser.add_argument("video", type=str)
    analyze_parser.add_argument("--out", type=str, default=None, help="Output directory.")
    analyze_parser.add_argument(
        "--mode", type=str, default="balanced", choices=["lightweight", "balanced", "performance"]
    )
    analyze_parser.add_argument("--height-m", type=float, default=None, dest="height_m")
    analyze_parser.add_argument(
        "--operated-side", type=str, default=None, choices=["L", "R"], dest="operated_side"
    )
    analyze_parser.add_argument(
        "--speed-class",
        type=str,
        default="comfortable",
        choices=["slow", "comfortable", "fast", "preferred"],
        dest="speed_class",
        help="norm band speed class to compare against (default: comfortable)",
    )
    analyze_parser.add_argument(
        "--side", type=str, default="auto", choices=["auto", "left", "right"]
    )
    analyze_parser.set_defaults(func=_cmd_analyze)

    probe_parser = subparsers.add_parser("probe", help="Print container/stream info for a video.")
    probe_parser.add_argument("video", type=str)
    probe_parser.set_defaults(func=_cmd_probe)

    args = parser.parse_args(argv)

    if args.version:
        from openacl import __version__

        print(__version__)
        return 0

    if not getattr(args, "command", None):
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

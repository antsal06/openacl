"""Command-line entry point. Phase 1 will add `analyze`, `report`, `sessions`."""

import sys


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    print("openacl 0.0.1 – Phase 0, noch kein Analysebefehl. Siehe docs/ROADMAP.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

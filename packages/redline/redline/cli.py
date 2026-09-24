"""The `redline` command line."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from redline.datasets.validate import validate_paths


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="redline")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate JSONL dataset files")
    validate.add_argument("paths", nargs="+", type=Path, metavar="FILE")
    validate.add_argument(
        "--allow-missing-parents",
        action="store_true",
        help="accept source.parent_id values not found in FILE (for checking a partial file)",
    )
    args = parser.parse_args(argv)

    paths: list[Path] = args.paths
    missing = [path for path in paths if not path.is_file()]
    if missing:
        for path in missing:
            print(f"{path}: not a file", file=sys.stderr)
        return 2
    return _validate(paths, allow_missing_parents=args.allow_missing_parents)


def _validate(paths: list[Path], *, allow_missing_parents: bool) -> int:
    report = validate_paths(paths, allow_missing_parents=allow_missing_parents)
    for error in report.errors:
        print(error, file=sys.stderr)
    if not report.ok:
        print(f"invalid: {len(report.errors)} error(s) in {len(paths)} file(s)", file=sys.stderr)
        return 1
    print(f"ok: {len(report.records)} record(s) in {len(paths)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

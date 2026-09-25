"""The `redline` command line."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from redline.datasets.load import DatasetError
from redline.datasets.validate import validate_paths
from redline.evaluate import EvalError, RunArtifactError, load_run, run_eval
from redline.judges.base import Judge
from redline.judges.keyword import KeywordJudge
from redline.judges.recorded import RecordedJudge, RecordingError
from redline.metrics.report import render_markdown


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="redline")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help="validate JSONL dataset files")
    validate.add_argument("paths", nargs="+", type=Path, metavar="FILE")

    evaluate = commands.add_parser("eval", help="run a judge over dataset files")
    evaluate.add_argument("paths", nargs="+", type=Path, metavar="FILE")
    evaluate.add_argument("--judge", required=True, choices=["keyword", "recorded"])
    evaluate.add_argument("--rules", type=Path, help="keyword rules JSON (--judge keyword)")
    evaluate.add_argument("--recording", type=Path, help="recorded judgments (--judge recorded)")
    evaluate.add_argument("--split", choices=["train", "val", "test"])
    evaluate.add_argument("--out", type=Path, default=Path("results"), help="default: results")
    evaluate.add_argument("--run-id")
    evaluate.add_argument("--concurrency", type=int, default=8)

    report = commands.add_parser("report", help="summarize an eval run as Markdown")
    report.add_argument("run_dir", type=Path, metavar="RUN_DIR")

    args = parser.parse_args(argv)
    if args.command == "report":
        return _report(args.run_dir)

    paths: list[Path] = args.paths
    if args.command == "eval":
        judge_file: Path | None = args.rules if args.judge == "keyword" else args.recording
        if judge_file is None:
            flag = "--rules" if args.judge == "keyword" else "--recording"
            print(f"--judge {args.judge} requires {flag}", file=sys.stderr)
            return 2
        paths = [*paths, judge_file]
    missing = [path for path in paths if not path.is_file()]
    if missing:
        for path in missing:
            print(f"{path}: not a file", file=sys.stderr)
        return 2
    if args.command == "validate":
        return _validate(paths)
    return _eval(args)


def _validate(paths: list[Path]) -> int:
    report = validate_paths(paths)
    for error in report.errors:
        print(error, file=sys.stderr)
    if not report.ok:
        print(f"invalid: {len(report.errors)} error(s) in {len(paths)} file(s)", file=sys.stderr)
        return 1
    print(f"ok: {len(report.records)} record(s) in {len(paths)} file(s)")
    return 0


def _eval(args: argparse.Namespace) -> int:
    try:
        judge: Judge
        if args.judge == "keyword":
            judge = KeywordJudge.from_file(args.rules)
        else:
            judge = RecordedJudge.from_file(args.recording)
    except (ValidationError, RecordingError) as exc:
        print(f"cannot load the {args.judge} judge: {exc}", file=sys.stderr)
        return 1
    if args.concurrency < 1:
        print("--concurrency must be at least 1", file=sys.stderr)
        return 2
    try:
        run = run_eval(
            args.paths,
            judge,
            out_dir=args.out,
            split=args.split,
            run_id=args.run_id,
            concurrency=args.concurrency,
        )
    except DatasetError as exc:
        for error in exc.errors:
            print(error, file=sys.stderr)
        print(f"invalid dataset: {len(exc.errors)} error(s)", file=sys.stderr)
        return 1
    except EvalError as exc:
        print(exc, file=sys.stderr)
        return 1
    metrics = run.metrics
    macro_f1 = "-" if metrics.macro is None else f"{metrics.macro.f1:.3f}"
    print(
        f"wrote {run.run_dir}: n {metrics.dataset.n}, macro F1 {macro_f1}, "
        f"judge errors {metrics.rates.judge_errors}"
    )
    return 0


def _report(run_dir: Path) -> int:
    if not run_dir.is_dir():
        print(f"{run_dir}: not a directory", file=sys.stderr)
        return 2
    try:
        metrics = load_run(run_dir)
    except RunArtifactError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(render_markdown(metrics), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())

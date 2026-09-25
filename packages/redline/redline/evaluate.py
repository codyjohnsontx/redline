"""Run a judge over a dataset and write one results directory per run.

results/<run_id>/
  metrics.json   the summary (redline.metrics.report.Metrics)
  items.jsonl    one ItemResult per evaluated record
  run.json       git sha, judge id, dataset hashes overall and per split, start and finish
                 times, cost
"""

import asyncio
import hashlib
import json
import secrets
import subprocess
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from redline.datasets.load import DatasetError
from redline.datasets.schema import VERDICTS_BY_DIRECTION, Record
from redline.datasets.splits import Split
from redline.datasets.validate import validate_paths
from redline.judges.base import DEFAULT_CONCURRENCY, Judge, JudgeInput, Judgment
from redline.metrics.report import DatasetInfo, ItemResult, Metrics, compute_metrics


class EvalError(Exception):
    pass


@dataclass(frozen=True)
class EvalRun:
    run_dir: Path
    metrics: Metrics


def run_eval(
    paths: Sequence[Path],
    judge: Judge,
    *,
    out_dir: Path,
    split: Split | None = None,
    run_id: str | None = None,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> EvalRun:
    """Judge every gold record in `paths` (optionally one split) and write the results.

    Records that are not gold yet are excluded and counted, never scored against a
    provisional label.
    """
    started = datetime.now(UTC)
    report = validate_paths(paths)
    if not report.ok:
        raise DatasetError(report.errors)
    records = [r.record for r in report.records if split is None or r.record.split == split]
    gold = [r for r in records if r.labels.gold_basis is not None]
    if not gold:
        raise EvalError(f"no gold records to evaluate in split {split or 'all'}")
    targets = sorted({r.target for r in gold})
    if len(targets) > 1:
        raise EvalError(f"records span several targets {targets}; evaluate one at a time")

    dataset_sha = _dataset_sha(gold)
    run_id = run_id or f"{started:%Y-%m-%dT%H%M%SZ}-{secrets.token_hex(2)}"
    run_dir = out_dir / run_id
    if run_dir.exists():
        raise EvalError(f"{run_dir} already exists; choose another run id")

    judgments = asyncio.run(
        judge.judge_many([JudgeInput.from_record(r) for r in gold], concurrency=concurrency)
    )
    items = [_item(record, judgment) for record, judgment in zip(gold, judgments, strict=True)]
    metrics = compute_metrics(
        run_id=run_id,
        target=targets[0],
        judge_id=judge.id,
        dataset=DatasetInfo(
            split=split,
            sha256=dataset_sha,
            n=len(gold),
            n_by_direction=dict(sorted(Counter(r.direction for r in gold).items())),
            n_excluded_not_gold=len(records) - len(gold),
        ),
        items=items,
    )

    run_dir.mkdir(parents=True)
    (run_dir / "metrics.json").write_text(metrics.model_dump_json(indent=2) + "\n", "utf-8")
    (run_dir / "items.jsonl").write_text(
        "".join(item.model_dump_json() + "\n" for item in items), "utf-8"
    )
    run_info = {
        "run_id": run_id,
        "git_sha": _git_sha(),
        "judge_id": judge.id,
        "files": [{"path": str(p), "sha256": _file_sha(p)} for p in paths],
        "dataset_sha256": dataset_sha,
        "dataset_sha256_by_split": _dataset_sha_by_split(gold),
        "started": started.isoformat(),
        "finished": datetime.now(UTC).isoformat(),
        "cost_usd": metrics.cost.usd if metrics.cost is not None else None,
    }
    (run_dir / "run.json").write_text(json.dumps(run_info, indent=2) + "\n", "utf-8")
    return EvalRun(run_dir, metrics)


def _item(record: Record, judgment: Judgment) -> ItemResult:
    """Score a judgment, treating a verdict the item's direction does not allow as an error."""
    verdict, category, error = judgment.verdict, judgment.category, judgment.error
    if verdict is not None and verdict not in VERDICTS_BY_DIRECTION[record.direction]:
        verdict, category = None, None
        error = f"verdict {judgment.verdict!r} is not valid for direction {record.direction!r}"
    return ItemResult(
        id=record.id,
        direction=record.direction,
        source_kind=record.source.kind,
        gold_verdict=record.verdict,
        gold_category=record.category,
        predicted_verdict=verdict,
        predicted_category=category,
        error=error,
        judge_id=judgment.judge_id,
        latency_ms=judgment.latency_ms,
        usage=judgment.usage,
    )


def load_metrics(run_dir: Path) -> Metrics:
    return Metrics.model_validate_json((run_dir / "metrics.json").read_bytes())


def _dataset_sha(records: Sequence[Record]) -> str:
    # Sorted canonical records, so the hash ignores file order and other splits.
    lines = sorted(r.model_dump_json() for r in records)
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _dataset_sha_by_split(records: Sequence[Record]) -> dict[str, str]:
    by_split: dict[str, list[Record]] = {}
    for record in records:
        by_split.setdefault(record.split or "unassigned", []).append(record)
    return {split: _dataset_sha(group) for split, group in sorted(by_split.items())}


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, timeout=5
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None

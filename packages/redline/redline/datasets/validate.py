"""Validate dataset files: each record on its own, then the files taken together."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from redline.datasets.load import LoadedRecord, RecordError, parse_jsonl


@dataclass
class ValidationReport:
    records: list[LoadedRecord] = field(default_factory=list[LoadedRecord])
    errors: list[RecordError] = field(default_factory=list[RecordError])

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_paths(paths: Sequence[Path]) -> ValidationReport:
    """Validate `paths` as one dataset.

    Every `source.parent_id` must resolve to a valid seed record of the same
    target among the records in `paths`.
    """
    report = ValidationReport()
    for path in paths:
        parsed = parse_jsonl(path)
        report.records.extend(parsed.records)
        report.errors.extend(parsed.errors)

    first_seen: dict[str, LoadedRecord] = {}
    for loaded in report.records:
        record_id = loaded.record.id
        if record_id in first_seen:
            first = first_seen[record_id]
            report.errors.append(
                RecordError(
                    loaded.path,
                    loaded.line,
                    f"id: duplicate id {record_id!r}, first seen at {first.path}:{first.line}",
                )
            )
        else:
            first_seen[record_id] = loaded

    for loaded in report.records:
        parent_id = loaded.record.source.parent_id
        if parent_id is None:
            continue
        parent = first_seen.get(parent_id)
        if parent is None:
            report.errors.append(
                RecordError(
                    loaded.path,
                    loaded.line,
                    f"source.parent_id: no valid record with id {parent_id!r} in the "
                    "validated files; include its seed file",
                )
            )
        elif parent.record.source.parent_id is not None:
            report.errors.append(
                RecordError(
                    loaded.path,
                    loaded.line,
                    f"source.parent_id: {parent_id!r} is not a root seed "
                    f"(its parent is {parent.record.source.parent_id!r}); "
                    "parent_id must name the root seed",
                )
            )
        elif parent.record.source.kind != "seed":
            report.errors.append(
                RecordError(
                    loaded.path,
                    loaded.line,
                    f"source.parent_id: {parent_id!r} is a {parent.record.source.kind!r} "
                    "record, not a seed; parent_id must name the root seed",
                )
            )
        elif parent.record.target != loaded.record.target:
            report.errors.append(
                RecordError(
                    loaded.path,
                    loaded.line,
                    f"target: {loaded.record.target!r} does not match target "
                    f"{parent.record.target!r} of its seed {parent_id!r}",
                )
            )
    return report

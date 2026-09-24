"""Validate dataset files: each record on its own, then the files taken together."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from redline.datasets.load import LoadedRecord, RecordError, parse_jsonl
from redline.datasets.splits import family_id, family_split_conflicts


@dataclass
class ValidationReport:
    records: list[LoadedRecord] = field(default_factory=list[LoadedRecord])
    errors: list[RecordError] = field(default_factory=list[RecordError])

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_paths(paths: Sequence[Path]) -> ValidationReport:
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

    conflicts = family_split_conflicts(loaded.record for loaded in report.records)
    for loaded in report.records:
        family = family_id(loaded.record)
        if family in conflicts:
            report.errors.append(
                RecordError(
                    loaded.path,
                    loaded.line,
                    f"split: family {family!r} spans splits {sorted(conflicts[family])}; "
                    "all variants of a seed must share one split",
                )
            )
    return report

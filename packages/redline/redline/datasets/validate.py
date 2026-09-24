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
    return report

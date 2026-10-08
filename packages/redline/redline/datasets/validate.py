"""Validate dataset files: each record on its own, then the files taken together."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from redline.datasets.categories import (
    CategoriesError,
    TargetCategories,
    categories_path,
    load_categories,
)
from redline.datasets.load import LoadedRecord, RecordError, parse_jsonl
from redline.datasets.schema import NO_CATEGORY, Record


@dataclass
class ValidationReport:
    records: list[LoadedRecord] = field(default_factory=list[LoadedRecord])
    errors: list[RecordError] = field(default_factory=list[RecordError])

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_paths(paths: Sequence[Path], targets_dir: Path | None = None) -> ValidationReport:
    """Validate `paths` as one dataset.

    Every `source.parent_id` must resolve to a valid seed record of the same
    target among the records in `paths`. With `targets_dir`, each record's
    categories, guide rule, and citations must also exist in
    `targets_dir/<target>/categories.yaml`.
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

    if targets_dir is not None:
        report.errors.extend(_check_categories(report.records, targets_dir))
    return report


def _check_categories(records: list[LoadedRecord], targets_dir: Path) -> list[RecordError]:
    """Check each record's categories, second-label category, guide rule, and citations.

    A target whose categories file cannot be loaded is reported once, at its first record.
    """
    errors: list[RecordError] = []
    loaded_targets: dict[str, TargetCategories | None] = {}
    for loaded in records:
        record = loaded.record
        messages: list[str] = []
        if record.target not in loaded_targets:
            try:
                loaded_targets[record.target] = load_categories(targets_dir, record.target)
            except CategoriesError as exc:
                loaded_targets[record.target] = None
                messages.append(f"target: record {record.id!r}: {exc}")
        target = loaded_targets[record.target]
        if target is not None:
            messages.extend(_category_problems(record, target, targets_dir))
        errors.extend(RecordError(loaded.path, loaded.line, m) for m in messages)
    return errors


def _category_problems(record: Record, target: TargetCategories, targets_dir: Path) -> list[str]:
    messages: list[str] = []
    where = categories_path(targets_dir, record.target)

    category = target.categories.get(record.category)
    if record.category != NO_CATEGORY and category is None:
        messages.append(
            f"category: record {record.id!r} names category {record.category!r}, "
            f"which is not a category in {where}"
        )
    for secondary in record.secondary_categories:
        if secondary not in target.categories:
            messages.append(
                f"secondary_categories: record {record.id!r} names category "
                f"{secondary!r}, which is not a category in {where}"
            )
    second = record.labels.second
    if (
        second is not None
        and second.category != NO_CATEGORY
        and second.category not in target.categories
    ):
        messages.append(
            f"labels.second.category: record {record.id!r} names category "
            f"{second.category!r}, which is not a category in {where}"
        )
    if (
        category is not None
        and record.guide_rule is not None
        and record.guide_rule not in category.rules
    ):
        messages.append(
            f"guide_rule: record {record.id!r} names rule {record.guide_rule!r}, "
            f"which is not a rule of category {record.category!r} in {where}"
        )
    for citation in record.citations:
        if citation not in target.citations:
            messages.append(
                f"citations: record {record.id!r} cites {citation!r}, "
                f"which is not a citation in {where}"
            )
    return messages

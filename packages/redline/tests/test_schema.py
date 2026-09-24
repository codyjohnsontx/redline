import json
from typing import Any

import pytest
from pydantic import ValidationError

from redline.datasets.schema import Record

from .conftest import sample_dicts


def by_id(record_id: str) -> dict[str, Any]:
    return next(r for r in sample_dicts() if r["id"] == record_id)


def rejects(record: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        Record.model_validate_json(json.dumps(record))


def test_samples_are_valid() -> None:
    for record in sample_dicts():
        Record.model_validate_json(json.dumps(record))


def test_redirect_is_not_an_output_verdict() -> None:
    record = by_id("fh-seed-002")
    record["verdict"] = "redirect"
    rejects(record, "verdict 'redirect' is not valid for direction 'output'")


def test_label_verdicts_are_checked_against_direction() -> None:
    record = by_id("fh-seed-002")
    record["labels"]["provisional"] = "redirect"
    rejects(record, "labels.provisional 'redirect' is not valid")


def test_unknown_verdict_is_rejected() -> None:
    record = by_id("fh-seed-001")
    record["verdict"] = "warn"
    rejects(record, "verdict")


def test_output_requires_user_prompt() -> None:
    record = by_id("fh-seed-002")
    record["context"]["user_prompt"] = None
    rejects(record, "requires context.user_prompt")


def test_input_must_not_carry_user_prompt() -> None:
    record = by_id("fh-seed-001")
    record["context"]["user_prompt"] = "hello"
    rejects(record, "must not set context.user_prompt")


def test_category_none_only_for_allow() -> None:
    record = by_id("fh-seed-001")
    record["category"] = "none"
    record["guide_rule"] = None
    record["citations"] = []
    rejects(record, "category 'none' is only valid for verdict 'allow'")


def test_category_requires_rule_and_citations() -> None:
    record = by_id("fh-seed-001")
    record["citations"] = []
    rejects(record, "requires guide_rule and citations")


def test_derived_source_requires_parent() -> None:
    record = by_id("fh-flip-001")
    del record["source"]["parent_id"]
    rejects(record, "requires source.parent_id")


def test_seed_must_not_have_parent() -> None:
    record = by_id("fh-seed-001")
    record["source"]["parent_id"] = "fh-seed-000"
    rejects(record, "must not have a source.parent_id")


def test_owner_gold_must_match_record() -> None:
    record = by_id("fh-seed-001")
    record["labels"]["owner"]["verdict"] = "block"
    rejects(record, "must match labels.owner")


def test_agreement_requires_labels_to_agree() -> None:
    record = by_id("fh-flip-001")
    record["labels"]["second"]["verdict"] = "redirect"
    rejects(record, "to agree")


def test_public_splits_hold_only_gold_records() -> None:
    record = by_id("fh-seed-001")
    record["labels"]["gold_basis"] = None
    rejects(record, "holds only gold records")


def test_unknown_fields_are_rejected() -> None:
    record = by_id("fh-seed-001")
    record["severity"] = "high"
    rejects(record, "severity")

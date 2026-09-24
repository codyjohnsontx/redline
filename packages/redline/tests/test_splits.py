import json
from collections import Counter

from redline.datasets.schema import Record
from redline.datasets.splits import assign_split, family_id

from .conftest import sample_dicts


def samples() -> list[Record]:
    return [Record.model_validate_json(json.dumps(r)) for r in sample_dicts()]


def test_variants_share_their_seed_family() -> None:
    by_id = {r.id: r for r in samples()}
    assert family_id(by_id["fh-flip-001"]) == "fh-seed-001"
    assert family_id(by_id["fh-seed-001"]) == "fh-seed-001"


# Splits are assigned once and must never move: a change to the hashing must fail here.
GOLDEN_SPLITS = {
    "fh-seed-001": "train",
    "fh-seed-002": "train",
    "fh-seed-004": "test",
    "fh-seed-010": "test",
    "golden-06": "val",
    "golden-07": "val",
}


def test_assign_split_matches_golden_vectors() -> None:
    assert {family: assign_split(family) for family in GOLDEN_SPLITS} == GOLDEN_SPLITS


def test_assign_split_matches_target_ratios() -> None:
    counts = Counter(assign_split(f"family-{i}") for i in range(10_000))
    assert abs(counts["train"] / 10_000 - 0.5) < 0.02
    assert abs(counts["val"] / 10_000 - 0.3) < 0.02
    assert abs(counts["test"] / 10_000 - 0.2) < 0.02


def test_samples_carry_their_family_split() -> None:
    for record in samples():
        assert record.split == assign_split(family_id(record))

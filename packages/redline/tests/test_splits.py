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


def test_assign_split_is_deterministic() -> None:
    assert assign_split("fh-seed-001") == assign_split("fh-seed-001")


def test_assign_split_matches_target_ratios() -> None:
    counts = Counter(assign_split(f"family-{i}") for i in range(10_000))
    assert abs(counts["train"] / 10_000 - 0.5) < 0.02
    assert abs(counts["val"] / 10_000 - 0.3) < 0.02
    assert abs(counts["test"] / 10_000 - 0.2) < 0.02


def test_samples_carry_their_family_split() -> None:
    for record in samples():
        assert record.split == assign_split(family_id(record))

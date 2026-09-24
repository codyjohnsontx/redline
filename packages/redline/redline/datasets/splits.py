"""Deterministic split assignment by seed family.

Every variant of a seed lands in the same split as the seed, so a paraphrase
family never leaks across train, val, and test.
"""

import hashlib
from collections.abc import Iterable

from redline.datasets.schema import Record, Split

# Cumulative upper bounds: 50 percent train, 30 percent val, 20 percent test.
SPLIT_BOUNDS: tuple[tuple[Split, float], ...] = (("train", 0.5), ("val", 0.8), ("test", 1.0))


def family_id(record: Record) -> str:
    """The seed a record descends from, or the record itself when it has no parent."""
    return record.source.parent_id or record.id


def assign_split(family: str) -> Split:
    """Map a family id to a split by a stable hash, independent of dataset order or size."""
    digest = hashlib.sha256(family.encode("utf-8")).digest()
    position = int.from_bytes(digest[:8], "big") / 2**64
    for split, bound in SPLIT_BOUNDS:
        if position < bound:
            return split
    return SPLIT_BOUNDS[-1][0]


def family_split_conflicts(records: Iterable[Record]) -> dict[str, set[Split]]:
    """Families whose records are spread over more than one split."""
    seen: dict[str, set[Split]] = {}
    for record in records:
        if record.split is not None:
            seen.setdefault(family_id(record), set()).add(record.split)
    return {family: splits for family, splits in seen.items() if len(splits) > 1}

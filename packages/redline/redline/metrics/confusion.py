"""Confusion matrices over verdicts."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ConfusionMatrix:
    """Rows are gold labels, columns predicted labels, both in `labels` order.

    A prediction of None is a judge error. It is counted in `errors` for its gold
    row rather than in any column, so an errored item is always a miss.
    """

    labels: tuple[str, ...]
    matrix: tuple[tuple[int, ...], ...]
    errors: tuple[int, ...]

    @classmethod
    def build(
        cls, labels: Sequence[str], pairs: Iterable[tuple[str, str | None]]
    ) -> "ConfusionMatrix":
        index = {label: i for i, label in enumerate(labels)}
        if len(index) != len(labels):
            raise ValueError(f"labels must be unique: {list(labels)}")
        counts = [[0] * len(labels) for _ in labels]
        errors = [0] * len(labels)
        for gold, predicted in pairs:
            row = _index(index, gold, "gold")
            if predicted is None:
                errors[row] += 1
            else:
                counts[row][_index(index, predicted, "predicted")] += 1
        return cls(tuple(labels), tuple(tuple(row) for row in counts), tuple(errors))


def _index(index: dict[str, int], label: str, role: str) -> int:
    try:
        return index[label]
    except KeyError:
        raise ValueError(f"{role} label {label!r} is not one of {list(index)}") from None

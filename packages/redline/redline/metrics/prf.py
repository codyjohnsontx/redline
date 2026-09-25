"""Per-category precision, recall, and F1, one category versus the rest."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryCounts:
    tp: int
    fp: int
    fn: int

    @property
    def support(self) -> int:
        """Gold positives: every item whose gold category is this one."""
        return self.tp + self.fn

    @property
    def precision(self) -> float | None:
        """None when the category was never predicted."""
        predicted = self.tp + self.fp
        return self.tp / predicted if predicted else None

    @property
    def recall(self) -> float | None:
        """None when the category has no gold positives."""
        return self.tp / self.support if self.support else None

    @property
    def f1(self) -> float:
        # 2TP / (2TP + FP + FN): defined whenever the category was gold or predicted.
        denominator = 2 * self.tp + self.fp + self.fn
        return 2 * self.tp / denominator if denominator else 0.0


@dataclass(frozen=True)
class Averages:
    precision: float
    recall: float
    f1: float


def category_counts(
    pairs: Iterable[tuple[str, str | None]], *, exclude: str
) -> dict[str, CategoryCounts]:
    """Count TP, FP, and FN per category from (gold, predicted) category pairs.

    Every category that appears as gold or predicted is reported, except `exclude`
    (the no-category id). A predicted None is a judge error: a miss for the gold
    category and a false positive for no category.
    """
    tp: dict[str, int] = {}
    fp: dict[str, int] = {}
    fn: dict[str, int] = {}
    for gold, predicted in pairs:
        for category in (gold, predicted):
            if category is not None and category != exclude:
                tp.setdefault(category, 0)
                fp.setdefault(category, 0)
                fn.setdefault(category, 0)
        if gold == predicted:
            if gold != exclude:
                tp[gold] += 1
            continue
        if gold != exclude:
            fn[gold] += 1
        if predicted is not None and predicted != exclude:
            fp[predicted] += 1
    return {c: CategoryCounts(tp[c], fp[c], fn[c]) for c in sorted(tp)}


def macro_average(counts: Mapping[str, CategoryCounts]) -> Averages | None:
    """The unweighted mean over categories with at least one gold positive."""
    return _average(counts, weighted=False)


def weighted_average(counts: Mapping[str, CategoryCounts]) -> Averages | None:
    """The mean over categories with gold positives, weighted by that support."""
    return _average(counts, weighted=True)


def _average(counts: Mapping[str, CategoryCounts], *, weighted: bool) -> Averages | None:
    scored = [c for c in counts.values() if c.support]
    if not scored:
        return None
    weights = [c.support if weighted else 1 for c in scored]
    total = sum(weights)

    def mean(values: list[float]) -> float:
        return sum(w * v for w, v in zip(weights, values, strict=True)) / total

    # A category that was never predicted has undefined precision; it averages as 0
    # so that never predicting a category cannot raise the average.
    return Averages(
        precision=mean([c.precision or 0.0 for c in scored]),
        recall=mean([c.recall or 0.0 for c in scored]),
        f1=mean([c.f1 for c in scored]),
    )

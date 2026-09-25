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
    # None when no averaged category was ever predicted.
    precision: float | None
    recall: float
    f1: float
    # Categories left out of the precision average because they were never predicted,
    # so their precision is undefined. Recall and F1 average over every category.
    precision_excluded: int


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

    def mean(pairs: list[tuple[CategoryCounts, float]]) -> float:
        weights = [c.support if weighted else 1 for c, _ in pairs]
        return sum(w * v for w, (_, v) in zip(weights, pairs, strict=True)) / sum(weights)

    precise = [(c, p) for c in scored if (p := c.precision) is not None]
    return Averages(
        precision=mean(precise) if precise else None,
        # Every scored category has support, so its recall is defined.
        recall=mean([(c, c.recall or 0.0) for c in scored]),
        f1=mean([(c, c.f1) for c in scored]),
        precision_excluded=len(scored) - len(precise),
    )

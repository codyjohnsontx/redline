"""Metrics against values computed by hand.

The per-category cases use eight (gold, predicted) category pairs:

    gold   pred        alpha    beta
    alpha  alpha       TP
    alpha  alpha       TP
    alpha  beta        FN       FP
    alpha  (error)     FN
    beta   beta                 TP
    beta   none                 FN
    none   alpha       FP
    none   none

alpha: TP 2, FP 1, FN 2 -> precision 2/3, recall 2/4, F1 4/7.
beta:  TP 1, FP 1, FN 1 -> precision 1/2, recall 1/2, F1 2/4.
"""

import pytest

from redline.metrics.confusion import ConfusionMatrix
from redline.metrics.intervals import wilson
from redline.metrics.prf import CategoryCounts, category_counts, macro_average, weighted_average

PAIRS: list[tuple[str, str | None]] = [
    ("alpha", "alpha"),
    ("alpha", "alpha"),
    ("alpha", "beta"),
    ("alpha", None),
    ("beta", "beta"),
    ("beta", "none"),
    ("none", "alpha"),
    ("none", "none"),
]


def test_category_counts_one_versus_rest() -> None:
    counts = category_counts(PAIRS, exclude="none")
    assert counts == {
        "alpha": CategoryCounts(tp=2, fp=1, fn=2),
        "beta": CategoryCounts(tp=1, fp=1, fn=1),
    }
    alpha, beta = counts["alpha"], counts["beta"]
    assert alpha.precision == pytest.approx(2 / 3)
    assert alpha.recall == pytest.approx(0.5)
    assert alpha.f1 == pytest.approx(4 / 7)
    assert beta.precision == pytest.approx(0.5)
    assert beta.recall == pytest.approx(0.5)
    assert beta.f1 == pytest.approx(0.5)


def test_macro_and_weighted_averages() -> None:
    counts = category_counts(PAIRS, exclude="none")
    macro = macro_average(counts)
    assert macro is not None
    assert macro.precision == pytest.approx((2 / 3 + 1 / 2) / 2)
    assert macro.recall == pytest.approx(0.5)
    assert macro.f1 == pytest.approx((4 / 7 + 1 / 2) / 2)
    # Supports are alpha 4, beta 2.
    weighted = weighted_average(counts)
    assert weighted is not None
    assert weighted.precision == pytest.approx((4 * 2 / 3 + 2 * 1 / 2) / 6)
    assert weighted.recall == pytest.approx(0.5)
    assert weighted.f1 == pytest.approx((4 * 4 / 7 + 2 * 1 / 2) / 6)


def test_averages_skip_categories_without_gold_and_zero_unpredicted_precision() -> None:
    # gamma is only ever predicted, so it has no support and is left out of the average;
    # delta is never predicted, so its undefined precision averages as 0.
    counts = category_counts(
        [("alpha", "alpha"), ("none", "gamma"), ("delta", "none")], exclude="none"
    )
    assert counts["gamma"].recall is None
    assert counts["gamma"].precision == 0.0
    assert counts["delta"].precision is None
    assert counts["delta"].f1 == 0.0
    macro = macro_average(counts)
    assert macro is not None
    assert macro.precision == pytest.approx(0.5)
    assert macro.recall == pytest.approx(0.5)
    assert macro.f1 == pytest.approx(0.5)


def test_averages_are_none_without_gold_positives() -> None:
    counts = category_counts([("none", "none"), ("none", "alpha")], exclude="none")
    assert macro_average(counts) is None
    assert weighted_average(counts) is None


def test_confusion_matrix_counts_errors_outside_the_columns() -> None:
    matrix = ConfusionMatrix.build(
        ["allow", "redirect", "block"],
        [
            ("allow", "allow"),
            ("allow", "block"),
            ("redirect", "allow"),
            ("block", "block"),
            ("block", "redirect"),
            ("block", None),
        ],
    )
    assert matrix.matrix == ((1, 0, 1), (1, 0, 0), (0, 1, 1))
    assert matrix.errors == (0, 0, 1)


def test_confusion_matrix_rejects_unknown_label() -> None:
    with pytest.raises(ValueError, match="predicted label 'redirect'"):
        ConfusionMatrix.build(["allow", "block"], [("allow", "redirect")])


@pytest.mark.parametrize(
    ("successes", "n", "low", "high"),
    [
        # Hand-computed with z = 1.96 from the Wilson score formula.
        (3, 4, 0.3006, 0.9544),
        (1, 4, 0.0456, 0.6994),
        (5, 5, 0.5655, 1.0),
        (0, 5, 0.0, 0.4345),
        (1, 3, 0.0615, 0.7923),
        (50, 100, 0.4038, 0.5962),
    ],
)
def test_wilson_matches_hand_computed(successes: int, n: int, low: float, high: float) -> None:
    interval = wilson(successes, n)
    assert interval is not None
    assert interval[0] == pytest.approx(low, abs=1e-4)
    assert interval[1] == pytest.approx(high, abs=1e-4)


def test_wilson_is_none_for_no_trials_and_rejects_impossible_counts() -> None:
    assert wilson(0, 0) is None
    with pytest.raises(ValueError):
        wilson(3, 2)

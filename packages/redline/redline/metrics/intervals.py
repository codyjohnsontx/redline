"""Confidence intervals for proportions."""

import math

# The two-sided 95 percent normal quantile.
Z_95 = 1.959963984540054


def wilson(successes: int, n: int, *, z: float = Z_95) -> tuple[float, float] | None:
    """The Wilson score interval for `successes` out of `n`, or None when `n` is 0.

    Unlike the normal approximation it stays inside [0, 1] and is not degenerate at
    0 or n successes, which matters at the 10 to 20 positives a category holds.
    """
    if n < 0 or not 0 <= successes <= n:
        raise ValueError(f"need 0 <= successes <= n, got {successes} of {n}")
    if n == 0:
        return None
    p = successes / n
    z2 = z * z
    denominator = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denominator
    return (max(0.0, center - half), min(1.0, center + half))

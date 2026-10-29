"""Statistical confidence intervals and uncertainty reporting for RAG evaluation."""

from __future__ import annotations

import math

from ragops.core.logging import get_logger

logger = get_logger(__name__)

ABSTENTION_PATTERNS: tuple[str, ...] = (
    "do not contain",
    "does not contain",
    "do not have",
    "does not have",
    "no information",
    "not mentioned",
    "cannot find",
    "cannot answer",
    "none of which address",
    "not provide any information",
    "insufficient information",
    "sufficient information",
    "not enough information",
    "not enough context",
    "cannot be answered",
    "provided documents do not",
    "insufficient context",
    "unsupported query",
)


def wilson_score_interval(
    successes: int,
    total: int,
    confidence: float = 0.95,
) -> dict[str, float]:
    """Calculate the Wilson score confidence interval for a binomial proportion.

    Provides asymmetric intervals that remain valid even for small sample sizes
    and extreme proportions (p = 0 or p = 1), avoiding the flaws of normal approximations.

    Args:
        successes: Number of successful outcomes.
        total: Total number of observations (sample size n).
        confidence: Desired confidence level (default 0.95 -> z = 1.95996).

    Returns:
        dict with keys: 'proportion', 'ci_lower', 'ci_upper', 'lower', 'upper', 'sample_size', 'successes'
    """
    if total <= 0:
        return {
            "proportion": 0.0,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
            "lower": 0.0,
            "upper": 0.0,
            "sample_size": 0,
            "successes": 0,
        }

    # Clamp successes between 0 and total
    k = max(0, min(successes, total))
    n = total
    p_hat = k / n

    # Standard normal quantile for two-sided interval
    # 0.95 -> 1.95996; 0.90 -> 1.64485; 0.99 -> 2.57583
    if abs(confidence - 0.95) < 0.01:
        z = 1.95996
    elif abs(confidence - 0.90) < 0.01:
        z = 1.64485
    elif abs(confidence - 0.99) < 0.01:
        z = 2.57583
    else:
        z = 1.95996

    z2 = z * z
    denom = 1.0 + (z2 / n)
    center = (p_hat + (z2 / (2.0 * n))) / denom
    margin = (z * math.sqrt(((p_hat * (1.0 - p_hat)) / n) + (z2 / (4.0 * (n ** 2))))) / denom

    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)

    return {
        "proportion": round(p_hat, 4),
        "ci_lower": round(lower, 4),
        "ci_upper": round(upper, 4),
        "lower": round(lower, 4),
        "upper": round(upper, 4),
        "sample_size": n,
        "successes": k,
    }


def is_grounded_abstention(actual_answer: str) -> bool:
    """Check if the model correctly abstained due to lack of grounding evidence."""
    if not actual_answer:
        return True
    answer_lower = actual_answer.lower()
    return any(phrase in answer_lower for phrase in ABSTENTION_PATTERNS)

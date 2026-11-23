"""Exam readiness: the probability of reaching a target score.

If question i is answered correctly with probability p_i, independently, the number of correct
answers follows a Poisson-binomial distribution. It is computed exactly with dynamic programming:

    dist[k] after question i  =  dist[k] * (1 - p_i)  +  dist[k - 1] * p_i
"""

from __future__ import annotations

import math


def score_distribution(probabilities: list[float]) -> list[float]:
    """dist[k] = P(exactly k of the questions are answered correctly)."""
    dist = [1.0]
    for p in probabilities:
        nxt = [0.0] * (len(dist) + 1)
        for k, mass in enumerate(dist):
            nxt[k] += mass * (1.0 - p)
            nxt[k + 1] += mass * p
        dist = nxt
    return dist


def pass_probability(probabilities: list[float], pass_fraction: float) -> float:
    """P(score >= pass_fraction of the questions), one question per probability."""
    if not probabilities:
        return 1.0
    needed = math.ceil(pass_fraction * len(probabilities) - 1e-9)
    return min(1.0, sum(score_distribution(probabilities)[needed:]))

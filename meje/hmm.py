"""Hidden Markov model inference: filtering, most likely path, log-likelihood.

Course topic: probabilistic reasoning over time (HMMs, week 7).
Notation follows Russell & Norvig, "Artificial Intelligence: A Modern Approach", ch. 14:
hidden state X_t, evidence e_t, belief b_t(x) = P(X_t = x | e_1..t).

The model is an input-output HMM, which is what a tutor needs:

* the transition matrix of a step depends on the teaching action taken at that step
  (reading a lesson moves knowledge differently from answering a question);
* a step may carry no evidence at all (a lesson is not a test).

One step therefore does two things, in this order:

    1. condition  b(x)  <- alpha * P(e_t | x) * b(x)          (Bayes' rule, skipped without evidence)
    2. predict    b(x') <- sum_x b(x) * P(x' | x, action_t)   (the learner changes by acting)

This is the same order as Bayesian Knowledge Tracing (Corbett & Anderson, 1995): the answer is
emitted by the knowledge state the learner had while answering, and learning happens afterwards.

Everything is plain Python lists so that each number can be checked by hand.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

Vector = list[float]
Matrix = list[list[float]]


@dataclass(frozen=True)
class Step:
    """One time step of the process.

    transition[i][j] = P(X_{t+1} = j | X_t = i, action_t)
    likelihood[i]    = P(e_t | X_t = i), or None when the step produced no evidence
    """

    transition: Matrix
    likelihood: Vector | None = None


@dataclass(frozen=True)
class FilterStep:
    """Everything the forward algorithm computed for one step (kept for the explanation UI)."""

    prior: Vector  # belief before the step
    posterior: Vector  # after conditioning on the evidence (equals prior without evidence)
    predicted: Vector  # after the transition: the belief the next step starts from
    evidence_probability: float | None  # P(e_t | e_1..t-1), None without evidence


def normalize(weights: Vector) -> tuple[Vector, float]:
    """Scale non-negative weights to sum to 1. Returns (distribution, original total)."""
    total = sum(weights)
    if total <= 0.0:
        raise ValueError("cannot normalise: the evidence has zero probability under the model")
    return [w / total for w in weights], total


def condition(belief: Vector, likelihood: Vector) -> tuple[Vector, float]:
    """Bayes' rule: posterior(x) = P(e | x) * belief(x) / P(e).

    Returns the posterior and the normaliser P(e) = sum_x P(e | x) * belief(x).
    """
    return normalize([likelihood[i] * belief[i] for i in range(len(belief))])


def predict(belief: Vector, transition: Matrix) -> Vector:
    """One step of the Markov chain: b'(j) = sum_i b(i) * T[i][j]."""
    size = len(belief)
    return [sum(belief[i] * transition[i][j] for i in range(size)) for j in range(size)]


def forward(prior: Vector, steps: list[Step]) -> list[FilterStep]:
    """Forward algorithm (filtering). O(T * S^2) time, O(S) memory per step.

    Returns one FilterStep per step; the last `predicted` is the current belief.
    """
    belief = list(prior)
    trace: list[FilterStep] = []
    for step in steps:
        if step.likelihood is None:
            posterior, evidence_probability = list(belief), None
        else:
            posterior, evidence_probability = condition(belief, step.likelihood)
        predicted = predict(posterior, step.transition)
        trace.append(FilterStep(list(belief), posterior, predicted, evidence_probability))
        belief = predicted
    return trace


def filtered_belief(prior: Vector, steps: list[Step]) -> Vector:
    """Current belief after all steps (the prior itself when there are none)."""
    trace = forward(prior, steps)
    return trace[-1].predicted if trace else list(prior)


def log_likelihood(prior: Vector, steps: list[Step]) -> float:
    """log P(e_1..T): the sum of the log normalisers of the forward pass."""
    return sum(
        math.log(s.evidence_probability)
        for s in forward(prior, steps)
        if s.evidence_probability is not None
    )


def viterbi(prior: Vector, steps: list[Step]) -> tuple[list[int], float]:
    """Most likely state sequence X_1 .. X_{T+1} given all evidence (Viterbi, 1967).

    X_t is the state during step t and X_{T+1} the state after the last transition, so the
    path has len(steps) + 1 entries. The recursion is the forward recursion with `sum`
    replaced by `max`, plus back-pointers; it runs in log space to avoid underflow.

    Returns (path as state indices, log probability of that path together with the evidence).
    """
    size = len(prior)
    neg_inf = float("-inf")

    def log(p: float) -> float:
        return math.log(p) if p > 0.0 else neg_inf

    def emit(t: int, state: int) -> float:
        if t < len(steps) and steps[t].likelihood is not None:
            return log(steps[t].likelihood[state])
        return 0.0  # no evidence: every state explains it equally well

    delta = [log(prior[s]) + emit(0, s) for s in range(size)]
    back: list[list[int]] = []
    for t, step in enumerate(steps):
        nxt, pointers = [], []
        for j in range(size):
            best_i = max(range(size), key=lambda i: (delta[i] + log(step.transition[i][j]), -i))
            pointers.append(best_i)
            nxt.append(delta[best_i] + log(step.transition[best_i][j]) + emit(t + 1, j))
        delta = nxt
        back.append(pointers)

    last = max(range(size), key=lambda s: (delta[s], -s))
    path = [last]
    for pointers in reversed(back):
        path.append(pointers[path[-1]])
    path.reverse()
    return path, delta[last]

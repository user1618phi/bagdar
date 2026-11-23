"""Real learners: fit the knowledge model to public answer logs and test its forecasts.

Data: ASSISTments 2009-2010 "skill builder" (corrected), a standard benchmark for knowledge
tracing: middle-school mathematics, 4,163 students, about 260,000 first-attempt answers on
145 skill tags. Source: Feng, Heffernan & Koedinger (2009), "Addressing the assessment challenge
with an online system that tutors as it assesses", UMUAI 19(3). Free for research use; the file
is downloaded on demand and is not redistributed with this repository.

What is done here, with the course's own tools:

* learning the HMM from data with the Baum-Welch algorithm (expectation-maximisation built on
  the forward-backward recursions), written from scratch;
* an honest test: students are split 80/20, the model never sees the test students, and every
  answer is forecast before it is read.

What this does and does not show. The logs contain only right/wrong answers to practice
problems, so they can test the "where is the learner" part (the HMM and its forecasts). They
cannot test the teaching policy or the route, because nobody in the data was taught by them.
The subject (school mathematics) also differs from the AI course, so the fitted numbers are
evidence that the method works on real people, not parameters for the course pack.

Run:  python -m meje realdata        (downloads the file once, writes docs/results_real.json)
"""

from __future__ import annotations

import csv
import json
import math
import time
import urllib.request
import zlib
from dataclasses import dataclass
from pathlib import Path

from .tutor import TutorModel

SOURCE_URL = "https://huggingface.co/datasets/OloriBern/assistments-dataset/resolve/main/skill_builder_data_corrected.csv"
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "data" / "assistments_2009_skill_builder.csv"
MAX_SEQUENCE = 200

Sequences = dict[tuple[str, str], list[int]]


@dataclass
class BinaryHMM:
    """A hidden Markov model over right/wrong answers. States are ordered from least to most knowing."""

    prior: list[float]
    transition: list[list[float]]
    p_correct: list[float]
    skill_prior: dict[str, list[float]] | None = None

    def start(self, skill: str) -> list[float]:
        if self.skill_prior and skill in self.skill_prior:
            return self.skill_prior[skill]
        return self.prior

    def forecast(self, skill: str, answers: list[int]) -> list[float]:
        """P(answer t is correct | answers before t), for every t: forecast first, then learn from it."""
        size = len(self.prior)
        belief = list(self.start(skill))
        forecasts = []
        for answer in answers:
            forecasts.append(sum(belief[s] * self.p_correct[s] for s in range(size)))
            weights = [belief[s] * (self.p_correct[s] if answer else 1.0 - self.p_correct[s]) for s in range(size)]
            total = sum(weights) or 1.0
            belief = [sum(weights[i] / total * self.transition[i][j] for i in range(size)) for j in range(size)]
        return forecasts


def download(path: Path = DEFAULT_CSV) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading the ASSISTments 2009-2010 skill builder data (64 MB) to {path} ...")
        urllib.request.urlretrieve(SOURCE_URL, path)
    return path


def load_sequences(path: Path) -> Sequences:
    """One sequence of 0/1 answers per (student, skill), in the order the student gave them.

    Standard cleaning for this dataset: keep main problems (original = 1), drop rows without a
    skill, order by order_id. A problem tagged with several skills carries a combined tag
    (for example "2_37_70"), which is treated as a skill of its own: 145 tags in all, 101 single
    skills and 44 combinations.
    """
    rows = []
    with open(path, encoding="latin-1", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["original"] == "1" and row["skill_id"] not in ("", "NA") and row["correct"] in ("0", "1"):
                rows.append((int(row["order_id"]), row["user_id"], row["skill_id"], int(row["correct"])))
    rows.sort()
    sequences: Sequences = {}
    for _, user, skill, correct in rows:
        answers = sequences.setdefault((user, skill), [])
        if len(answers) < MAX_SEQUENCE:
            answers.append(correct)
    return sequences


def split_by_student(sequences: Sequences, test_share: float = 0.2) -> tuple[Sequences, Sequences]:
    """Deterministic split: a student is entirely in training or entirely in the test set."""
    train, test = {}, {}
    for key, answers in sequences.items():
        bucket = zlib.crc32(key[0].encode()) % 1000 / 1000.0
        (test if bucket < test_share else train)[key] = answers
    return train, test


def baum_welch(sequences: Sequences, model: BinaryHMM, iterations: int = 30, tolerance: float = 1e-5,
               per_skill_prior: bool = False, prior_strength: float = 5.0) -> tuple[BinaryHMM, list[float]]:
    """Fit the HMM by expectation-maximisation (Baum et al., 1970; Rabiner, 1989).

    E-step: scaled forward-backward gives, for every answer, the posterior of each hidden state
    (gamma) and of each transition (xi). M-step: re-estimate prior, transitions and emissions
    from those expected counts. Transitions that start at zero stay at zero, so the
    "knowledge never moves backwards" structure is preserved. Stops when the mean log-likelihood
    per answer improves by less than `tolerance`. Returns the model and the likelihood history.
    """
    size = len(model.prior)
    states = range(size)
    history: list[float] = []
    total_answers = sum(len(a) for a in sequences.values())
    for _ in range(iterations):
        prior_count = [1e-6] * size
        trans_count = [[0.0] * size for _ in states]
        right_count = [1e-6] * size
        seen_count = [2e-6] * size
        skill_count: dict[str, list[float]] = {}
        log_likelihood = 0.0
        transition, p_correct = model.transition, model.p_correct
        emit = ([1.0 - p for p in p_correct], list(p_correct))

        for (_, skill), answers in sequences.items():
            n = len(answers)
            if n == 0:
                continue
            start = model.start(skill)
            alphas, scales = [], []
            current = [start[s] * emit[answers[0]][s] for s in states]
            for t in range(n):
                if t:
                    previous = alphas[-1]
                    e = emit[answers[t]]
                    current = [sum(previous[i] * transition[i][j] for i in states) * e[j] for j in states]
                scale = sum(current) or 1e-300
                alphas.append([value / scale for value in current])
                scales.append(scale)
                log_likelihood += math.log(scale)
            beta = [1.0] * size
            for t in range(n - 1, -1, -1):
                alpha = alphas[t]
                gamma = [alpha[s] * beta[s] for s in states]
                norm = sum(gamma) or 1e-300
                answer = answers[t]
                for s in states:
                    g = gamma[s] / norm
                    seen_count[s] += g
                    if answer:
                        right_count[s] += g
                    if t == 0:
                        prior_count[s] += g
                        if per_skill_prior:
                            skill_count.setdefault(skill, [0.0] * size)[s] += g
                if t:
                    e = emit[answer]
                    previous = alphas[t - 1]
                    weighted = [e[j] * beta[j] / scales[t] for j in states]
                    for i in states:
                        row, a = transition[i], previous[i]
                        if a:
                            for j in states:
                                if row[j]:
                                    trans_count[i][j] += a * row[j] * weighted[j]
                    beta = [sum(transition[i][j] * weighted[j] for j in states) for i in states]

        history.append(log_likelihood / total_answers)
        prior_total = sum(prior_count)
        new_prior = [c / prior_total for c in prior_count]
        new_transition = []
        for i in states:
            row_total = sum(trans_count[i])
            new_transition.append([c / row_total for c in trans_count[i]] if row_total > 0 else list(transition[i]))
        skill_prior = None
        if per_skill_prior:
            skill_prior = {}
            for skill, counts in skill_count.items():
                smoothed = [counts[s] + prior_strength * new_prior[s] for s in states]
                skill_prior[skill] = [value / sum(smoothed) for value in smoothed]
        model = BinaryHMM(new_prior, new_transition, [right_count[s] / seen_count[s] for s in states], skill_prior)
        if len(history) > 1 and history[-1] - history[-2] < tolerance:
            break
    return model, history


def auc(pairs: list[tuple[float, int]]) -> float:
    """Area under the ROC curve from ranks (ties get the average rank)."""
    ordered = sorted(pairs)
    rank_sum, index, positives = 0.0, 0, sum(label for _, label in pairs)
    while index < len(ordered):
        end = index
        while end + 1 < len(ordered) and ordered[end + 1][0] == ordered[index][0]:
            end += 1
        average_rank = (index + end) / 2 + 1
        rank_sum += average_rank * sum(label for _, label in ordered[index:end + 1])
        index = end + 1
    negatives = len(pairs) - positives
    if positives == 0 or negatives == 0:
        return 0.5
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def score(pairs: list[tuple[float, int]]) -> dict:
    n = len(pairs)
    bins = []
    for low in range(10):
        chosen = [(p, y) for p, y in pairs if low / 10 <= p < (low + 1) / 10 or (low == 9 and p >= 1.0)]
        if chosen:
            bins.append({"range": [low / 10, (low + 1) / 10], "n": len(chosen),
                         "forecast": sum(p for p, _ in chosen) / len(chosen), "observed": sum(y for _, y in chosen) / len(chosen)})
    clip = lambda p: min(1 - 1e-9, max(1e-9, p))
    return {
        "auc": auc(pairs),
        "brier": sum((p - y) ** 2 for p, y in pairs) / n,
        "log_loss": -sum(math.log(clip(p)) if y else math.log(1 - clip(p)) for p, y in pairs) / n,
        "accuracy": sum((p >= 0.5) == bool(y) for p, y in pairs) / n,
        "calibration_error": sum(b["n"] * abs(b["forecast"] - b["observed"]) for b in bins) / n,
        "bins": bins,
    }


def run(path: Path = DEFAULT_CSV, iterations: int = 30) -> dict:
    started = time.perf_counter()
    sequences = load_sequences(download(path))
    train, test = split_by_student(sequences)
    train_answers = [a for answers in train.values() for a in answers]
    base_rate = sum(train_answers) / len(train_answers)
    by_skill: dict[str, list[int]] = {}
    for (_, skill), answers in train.items():
        tally = by_skill.setdefault(skill, [0, 0])
        tally[0] += sum(answers)
        tally[1] += len(answers)
    skill_mean = {skill: (right + base_rate) / (count + 1) for skill, (right, count) in by_skill.items()}

    assumed = TutorModel()
    assumed_model = BinaryHMM(list(assumed.prior), assumed.transition("practice"), list(assumed.p_correct))
    bkt, bkt_history = baum_welch(train, BinaryHMM([0.6, 0.4], [[0.8, 0.2], [0.0, 1.0]], [0.2, 0.9]), iterations)
    fitted, fitted_history = baum_welch(train, assumed_model, iterations)
    per_skill, per_skill_history = baum_welch(train, fitted, iterations, per_skill_prior=True)

    def running_average(skill: str, answers: list[int]) -> list[float]:
        mean = skill_mean.get(skill, base_rate)
        forecasts, right = [], 0
        for n, answer in enumerate(answers):
            forecasts.append((mean * 2 + right) / (2 + n))
            right += answer
        return forecasts

    forecasters = {
        "Always the average": lambda skill, answers: [base_rate] * len(answers),
        "Skill average": lambda skill, answers: [skill_mean.get(skill, base_rate)] * len(answers),
        "Student's running average": running_average,
        "BKT, 2 states, fitted": bkt.forecast,
        "Meje HMM, assumed numbers": assumed_model.forecast,
        "Meje HMM, fitted": fitted.forecast,
        "Meje HMM, fitted, prior per skill": per_skill.forecast,
    }
    results = []
    for name, forecast in forecasters.items():
        pairs = [(p, y) for (_, skill), answers in test.items() for p, y in zip(forecast(skill, answers), answers)]
        results.append({"model": name, **score(pairs)})

    return {
        "dataset": "ASSISTments 2009-2010 skill builder (corrected)",
        "citation": "Feng, Heffernan & Koedinger (2009), User Modeling and User-Adapted Interaction 19(3), 243-266",
        "source": SOURCE_URL,
        "note": "Real students. Tests the knowledge model's forecasts only; the teaching policy and the route cannot be "
                "tested on logs of students who were not taught by them. School mathematics, not the AI course.",
        "students": {"train": len({u for u, _ in train}), "test": len({u for u, _ in test})},
        "answers": {"train": len(train_answers), "test": sum(len(a) for a in test.values())},
        "skills": len({s for _, s in sequences}),
        "base_rate": base_rate,
        "models": results,
        "parameters": {
            "assumed": {"prior": assumed_model.prior, "transition": assumed_model.transition, "p_correct": assumed_model.p_correct},
            "fitted": {"prior": fitted.prior, "transition": fitted.transition, "p_correct": fitted.p_correct},
            "bkt": {"prior": bkt.prior, "transition": bkt.transition, "p_correct": bkt.p_correct},
        },
        "em": {"bkt_sweeps": len(bkt_history), "hmm_sweeps": len(fitted_history), "per_skill_sweeps": len(per_skill_history),
               "log_likelihood_first": fitted_history[0], "log_likelihood_last": fitted_history[-1]},
        "seconds": time.perf_counter() - started,
    }


def print_summary(results: dict) -> None:
    print(f"\n{results['dataset']}: {results['students']['train']} students to fit, {results['students']['test']} held out, "
          f"{results['answers']['test']} held-out answers on {results['skills']} skills")
    print(f"  {'forecaster':<38}{'AUC':>7}{'Brier':>8}{'log loss':>10}{'accuracy':>10}{'calib. err':>12}")
    for row in results["models"]:
        print(f"  {row['model']:<38}{row['auc']:>7.3f}{row['brier']:>8.4f}{row['log_loss']:>10.4f}{row['accuracy']:>10.1%}{row['calibration_error']:>12.3f}")
    fitted = results["parameters"]["fitted"]
    print(f"  fitted prior {[round(p, 3) for p in fitted['prior']]}, P(correct | state) {[round(p, 3) for p in fitted['p_correct']]}")
    print(f"  fitted transitions {[[round(p, 3) for p in row] for row in fitted['transition']]}")
    print(f"  EM: {results['em']['hmm_sweeps']} sweeps, log-likelihood per answer {results['em']['log_likelihood_first']:.4f} -> "
          f"{results['em']['log_likelihood_last']:.4f}; {results['seconds']:.0f} s")

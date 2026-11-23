"""Simulation experiments: does each algorithm do its job, and do they beat simple baselines?

Simulated learners have a true hidden state per skill. The tutor never sees it: it only sees
answers, exactly as with a real learner. This lets us measure things that are impossible to
measure on real people (was the skill truly mastered when the tutor moved on?).

What this evidence is and is not:
* it verifies the implementation and compares decision rules under stated assumptions;
* it is NOT evidence of learning gains in real students. Three kinds of learner are used:
  "matched" follows the model the tutor assumes (a policy tested on its own model wins by
  construction); "mismatched" has the same structure but different numbers; "foreign" is built
  on a different theory (continuous ability, no discrete states). The last two show how much of
  the advantage survives when the tutor's model is wrong.

Run:  python -m meje experiments      (writes docs/results.json, deterministic for a given seed)
"""

from __future__ import annotations

import json
import math
import random
import time
from dataclasses import replace
from pathlib import Path
from typing import Callable

from . import mdp, search
from .content import load_pack
from .tutor import ACTIONS, STATES, M, Tutor, TutorModel, U, observation_of

Policy = Callable[[list[float], dict], str]

# A learner who breaks the tutor's assumptions: luckier guesses, more slips, slower learning.
MISMATCHED = replace(
    TutorModel(),
    prior=(0.60, 0.30, 0.10),
    p_correct=(0.35, 0.55, 0.85),
    transition_explain=((0.55, 0.45, 0.00), (0.00, 0.90, 0.10), (0.00, 0.00, 1.00)),
    transition_practice=((0.95, 0.05, 0.00), (0.00, 0.75, 0.25), (0.00, 0.00, 1.00)),
)


def _sample(rng: random.Random, distribution) -> int:
    threshold, total = rng.random(), 0.0
    for index, p in enumerate(distribution):
        total += p
        if threshold < total:
            return index
    return len(distribution) - 1


class HmmLearner:
    """A learner who follows a three-state model (the tutor's own, or a perturbed one)."""

    def __init__(self, model: TutorModel) -> None:
        self.model = model

    def start(self, rng: random.Random):
        return _sample(rng, self.model.prior)

    def answer(self, state, rng: random.Random) -> tuple[bool, bool]:
        correct = rng.random() < self.model.p_correct[state]
        p_sure = self.model.p_sure_given_correct[state] if correct else self.model.p_sure_given_wrong[state]
        return correct, rng.random() < p_sure

    def learn(self, state, action: str, rng: random.Random):
        return _sample(rng, self.model.transition(action)[state])

    def label(self, state) -> int:
        return state


class LogisticLearner:
    """A learner built on a different theory: continuous ability, no discrete states at all.

    P(correct) follows an item-response curve with a 25% guessing floor; every action moves the
    ability by a noisy amount with diminishing returns. The tutor's three-state model is
    structurally wrong for this learner, which is the point of the test.
    """

    @staticmethod
    def _sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    def start(self, rng: random.Random):
        return rng.gauss(-0.6, 1.3)

    def answer(self, ability, rng: random.Random) -> tuple[bool, bool]:
        correct = rng.random() < 0.25 + 0.75 * self._sigmoid(1.7 * ability)
        confidence = self._sigmoid(1.4 * ability)
        return correct, rng.random() < (confidence if correct else 0.1 + 0.4 * confidence)

    def learn(self, ability, action: str, rng: random.Random):
        if action == "explain":  # instruction helps most when little is known
            gain = 1.1 * self._sigmoid(-ability)
        else:  # retrieval helps most once there is something to retrieve
            gain = 0.25 + 0.55 * self._sigmoid(ability + 0.5) * self._sigmoid(2.0 - ability)
        return ability + max(0.0, rng.gauss(gain, 0.25))

    def label(self, ability) -> int:
        return 0 if ability < -0.7 else 2 if ability >= 1.0 else 1


LEARNERS = {
    "matched": lambda tutor: HmmLearner(tutor.model),
    "mismatched": lambda tutor: HmmLearner(MISMATCHED),
    "foreign": lambda tutor: LogisticLearner(),
}


def make_policies(tutor: Tutor) -> dict[str, Policy]:
    """The tutor's decision rule and the baselines it is compared against."""

    def meje(belief, memory):
        if memory["steps"] >= tutor.model.max_steps_per_skill:
            return "advance"
        return mdp.greedy_action(tutor.action_values(belief))

    def lookahead(belief, memory):  # ablation: one step of expectimax over the possible answers
        if memory["steps"] >= tutor.model.max_steps_per_skill:
            return "advance"
        return mdp.greedy_action(tutor.lookahead_values(belief, depth=1))

    def streak(belief, memory):  # common mastery heuristic: three correct answers in a row
        if memory["streak"] >= 3:
            return "advance"
        return "explain" if memory["last_wrong"] else "practice"

    def fixed(belief, memory):  # the same dose for everyone: one lesson, three questions
        return ("explain", "practice", "practice", "practice", "advance")[min(memory["steps"], 4)]

    def lesson_only(belief, memory):  # read twice, never tested
        return "explain" if memory["steps"] < 2 else "advance"

    def oracle(belief, memory):  # upper bound: sees the true state
        return tutor.solution.policy[memory["true_state"]]

    return {"Meje (HMM + MDP)": meje, "Meje + lookahead": lookahead, "3-in-a-row": streak,
            "Fixed dose": fixed, "Lessons only": lesson_only, "Oracle (sees truth)": oracle}


def run_episode(tutor: Tutor, learner, policy: Policy, rng: random.Random, max_steps: int = 60) -> dict:
    """One learner, one skill, until the policy advances."""
    state = learner.start(rng)
    belief = list(tutor.model.prior)
    memory = {"steps": 0, "streak": 0, "last_wrong": False, "true_state": learner.label(state)}
    minutes, forecasts, tracking = 0.0, [], []
    while memory["steps"] < max_steps:
        action = policy(belief, memory)
        if action == "advance":
            break
        truth = learner.label(state)
        tracking.append((belief[truth], max(range(3), key=lambda s: belief[s]) == truth))
        minutes += tutor.model.minutes_of(action)
        if action == "practice":
            correct, sure = learner.answer(state, rng)
            forecasts.append((tutor.p_correct(belief), correct))
            likelihood = tutor.model.likelihood(observation_of(correct, sure))
            total = sum(likelihood[s] * belief[s] for s in range(3))
            belief = [likelihood[s] * belief[s] / total for s in range(3)]
            memory["streak"] = memory["streak"] + 1 if correct else 0
            memory["last_wrong"] = not correct
        else:
            memory["last_wrong"] = False
        table = tutor.model.transition(action)
        belief = [sum(belief[i] * table[i][j] for i in range(3)) for j in range(3)]
        state = learner.learn(state, action, rng)
        memory["steps"] += 1
        memory["true_state"] = learner.label(state)
    final = learner.label(state)
    return {"minutes": minutes, "state": final, "forecasts": forecasts, "tracking": tracking,
            "payoff": tutor.model.reward_advance[final] - minutes}


def compare_policies(tutor: Tutor, learner, episodes: int, seed: int) -> list[dict]:
    rows = []
    for name, policy in make_policies(tutor).items():
        rng = random.Random(seed)  # same seed for every rule; streams diverge once rules act differently (unpaired comparison)
        runs = [run_episode(tutor, learner, policy, rng) for _ in range(episodes)]
        n = len(runs)
        rows.append({
            "policy": name,
            "minutes": sum(r["minutes"] for r in runs) / n,
            "mastered": sum(r["state"] == M for r in runs) / n,
            "left_unknown": sum(r["state"] == U for r in runs) / n,
            "payoff": sum(r["payoff"] for r in runs) / n,
        })
    return rows


def calibration(tutor: Tutor, learner, episodes: int, seed: int) -> dict:
    """Are the HMM's forecasts honest? When it says 70%, is the learner right 70% of the time?"""
    rng = random.Random(seed)
    policy = make_policies(tutor)["Meje (HMM + MDP)"]
    forecasts, tracking = [], []
    for _ in range(episodes):
        run = run_episode(tutor, learner, policy, rng)
        forecasts += run["forecasts"]
        tracking += run["tracking"]
    base_rate = sum(c for _, c in forecasts) / len(forecasts)
    bins = []
    for low in range(10):
        chosen = [(p, c) for p, c in forecasts if low / 10 <= p < (low + 1) / 10 or (low == 9 and p == 1.0)]
        if chosen:
            bins.append({"range": [low / 10, (low + 1) / 10], "n": len(chosen),
                         "forecast": sum(p for p, _ in chosen) / len(chosen),
                         "observed": sum(c for _, c in chosen) / len(chosen)})
    return {
        "answers": len(forecasts),
        "brier": sum((p - c) ** 2 for p, c in forecasts) / len(forecasts),
        "brier_base_rate": base_rate * (1 - base_rate),
        "expected_calibration_error": sum(b["n"] * abs(b["forecast"] - b["observed"]) for b in bins) / len(forecasts),
        "bins": bins,
        "probability_on_true_state": sum(p for p, _ in tracking) / len(tracking),
        "map_accuracy": sum(hit for _, hit in tracking) / len(tracking),
    }


def compare_search(tutor: Tutor, profiles: int, seed: int) -> list[dict]:
    """A* against uninformed and greedy search on route problems with random learner beliefs."""
    rng = random.Random(seed)
    rows = []
    for destination in tutor.pack.destinations:
        totals = {name: {"expanded": 0, "cost": 0.0, "optimal": 0, "seconds": 0.0} for name in ("A*", "UCS", "Greedy", "BFS")}
        for _ in range(profiles):
            beliefs = {}
            for sid in tutor.pack.skills:
                weights = [rng.random() ** 2 for _ in STATES]
                beliefs[sid] = [w / sum(weights) for w in weights]
            problem = tutor.route_problem(frozenset(), frozenset(destination["targets"]), beliefs)
            runs = {}
            for name, solve in (("A*", lambda p: search.astar(p, p.heuristic, 0)), ("UCS", search.uniform_cost_search),
                                ("Greedy", lambda p: search.greedy_best_first(p, p.heuristic)), ("BFS", search.breadth_first_search)):
                started = time.perf_counter()
                runs[name] = solve(problem)
                totals[name]["seconds"] += time.perf_counter() - started
            optimum = runs["UCS"].cost
            for name, result in runs.items():
                totals[name]["expanded"] += result.expanded
                totals[name]["cost"] += result.cost / optimum
                totals[name]["optimal"] += abs(result.cost - optimum) < 1e-9
        rows.append({
            "destination": destination["name"], "required_skills": len(problem.required), "relevant_skills": len(problem.relevant),
            "algorithms": [
                {"algorithm": name, "expanded": t["expanded"] / profiles, "cost_ratio": t["cost"] / profiles,
                 "optimal_share": t["optimal"] / profiles, "milliseconds": 1000 * t["seconds"] / profiles}
                for name, t in totals.items()
            ],
        })
    return rows


def run_all(episodes: int = 20_000, profiles: int = 200, seed: int = 7) -> dict:
    tutor = Tutor(load_pack())
    return {
        "seed": seed, "episodes": episodes, "profiles": profiles,
        "note": "Simulated learners. Verifies the implementation and compares decision rules under stated "
                "assumptions; it is not evidence of learning gains in real students.",
        "policies": {name: compare_policies(tutor, build(tutor), episodes, seed) for name, build in LEARNERS.items()},
        "calibration": {name: calibration(tutor, build(tutor), episodes, seed) for name, build in LEARNERS.items()},
        "search": compare_search(tutor, profiles, seed),
        "mdp": {"iterations": tutor.solution.iterations, "policy": dict(zip(STATES, tutor.solution.policy)),
                "values": dict(zip(STATES, tutor.solution.values)), "advance_threshold": tutor.advance_threshold(),
                "actions": list(ACTIONS)},
    }


def write_results(path: Path, **kwargs) -> dict:
    results = run_all(**kwargs)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return results


def print_summary(results: dict) -> None:
    for label in LEARNERS:
        print(f"\nTeaching policies, {label} learners ({results['episodes']} skills each)")
        print(f"  {'policy':<24}{'minutes':>9}{'mastered':>10}{'left unknown':>14}{'payoff':>9}")
        for row in results["policies"][label]:
            print(f"  {row['policy']:<24}{row['minutes']:>9.2f}{row['mastered']:>10.1%}{row['left_unknown']:>14.1%}{row['payoff']:>9.2f}")
        cal = results["calibration"][label]
        print(f"  HMM forecasts: Brier {cal['brier']:.4f} (base rate {cal['brier_base_rate']:.4f}), "
              f"calibration error {cal['expected_calibration_error']:.3f}, true state is the top guess {cal['map_accuracy']:.1%}")
    print(f"\nRoute search, {results['profiles']} random belief profiles per destination (mean nodes expanded)")
    print(f"  {'destination':<14}{'A*':>8}{'UCS':>9}{'Greedy':>9}{'BFS':>9}   optimal: A* / Greedy / BFS")
    for row in results["search"]:
        by = {a["algorithm"]: a for a in row["algorithms"]}
        print(f"  {row['destination']:<14}{by['A*']['expanded']:>8.1f}{by['UCS']['expanded']:>9.1f}{by['Greedy']['expanded']:>9.1f}"
              f"{by['BFS']['expanded']:>9.1f}   {by['A*']['optimal_share']:.0%} / {by['Greedy']['optimal_share']:.0%} / {by['BFS']['optimal_share']:.0%}")

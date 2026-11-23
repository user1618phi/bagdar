"""State-space search: A*, uniform-cost, greedy best-first and breadth-first search.

Course topic: search and heuristics (week 2).
Notation follows Russell & Norvig, AIMA ch. 3: g(n) path cost so far, h(n) heuristic estimate
of the remaining cost, f(n) = g(n) + h(n).

`RouteProblem` is the learning-route problem that Meje solves:

    state      the set of skills already completed
    action     study one skill whose hard prerequisites are all completed
    step cost  expected minutes to master that skill, taken from the learner's current belief
               (HMM) and the optimal teaching policy (MDP); each missing *soft* prerequisite
               makes the skill slower by `soft_penalty`
    goal       every target skill is completed

Soft prerequisites create a real choice (study the helpful topic first, or skip it and pay the
penalty), which is why this is a search problem and not a topological sort.
"""

from __future__ import annotations

import heapq
import itertools
import math
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Hashable, Iterable, Protocol

State = Hashable


class Problem(Protocol):
    initial: State

    def is_goal(self, state: State) -> bool: ...

    def successors(self, state: State) -> Iterable[tuple[str, State, float]]: ...


@dataclass
class SearchResult:
    algorithm: str
    actions: list[str]  # the plan; empty when the start is already a goal
    cost: float  # total path cost (inf when no plan exists)
    expanded: int  # nodes taken off the frontier and expanded
    generated: int  # successor nodes created
    max_frontier: int
    log: list[dict] = field(default_factory=list)  # first expansions, for the explanation UI

    @property
    def found(self) -> bool:
        return self.cost != float("inf")


def best_first_search(
    problem: Problem,
    priority: Callable[[float, State], float],
    algorithm: str,
    heuristic: Callable[[State], float] | None = None,
    log_limit: int = 60,
) -> SearchResult:
    """Generic best-first graph search with a priority queue.

    `priority(g, state)` is the evaluation function f. A node is goal-tested when it is
    *expanded*, not when it is generated: that is what makes UCS and A* optimal.
    A state is re-opened if a cheaper path to it appears, so the search stays correct even
    with an inconsistent heuristic.
    """
    counter = itertools.count()  # tie-break: deterministic, never compares states
    start = problem.initial
    frontier: list[tuple[float, float, int, State]] = [(priority(0.0, start), 0.0, next(counter), start)]
    best_g: dict[State, float] = {start: 0.0}
    parent: dict[State, tuple[State, str] | None] = {start: None}
    expanded = generated = 0
    max_frontier = 1
    log: list[dict] = []

    while frontier:
        f, neg_g, _, state = heapq.heappop(frontier)
        g = -neg_g if neg_g else 0.0
        if g > best_g.get(state, float("inf")) + 1e-12:
            continue  # stale entry: a cheaper path to this state was found later
        if len(log) < log_limit:
            log.append({"state": state, "g": g, "h": heuristic(state) if heuristic else 0.0, "f": f})
        if problem.is_goal(state):
            return SearchResult(algorithm, _plan(parent, state), g, expanded, generated, max_frontier, log)
        expanded += 1
        for action, nxt, step_cost in problem.successors(state):
            if step_cost < 0:
                raise ValueError("step costs must be non-negative")
            new_g = g + step_cost
            if new_g + 1e-12 < best_g.get(nxt, float("inf")):
                best_g[nxt] = new_g
                parent[nxt] = (state, action)
                generated += 1
                # equal f: prefer the deeper node (larger g) to reach a goal sooner
                heapq.heappush(frontier, (priority(new_g, nxt), -new_g, next(counter), nxt))
        max_frontier = max(max_frontier, len(frontier))
    return SearchResult(algorithm, [], float("inf"), expanded, generated, max_frontier, log)


def astar(problem: Problem, heuristic: Callable[[State], float], log_limit: int = 60) -> SearchResult:
    """A* search: f = g + h. Optimal when h is consistent (Hart, Nilsson & Raphael, 1968)."""
    return best_first_search(problem, lambda g, s: g + heuristic(s), "A*", heuristic, log_limit)


def uniform_cost_search(problem: Problem, log_limit: int = 0) -> SearchResult:
    """Uniform-cost search: f = g. Optimal, but blind: it is A* with h = 0."""
    return best_first_search(problem, lambda g, s: g, "UCS", None, log_limit)


def greedy_best_first(problem: Problem, heuristic: Callable[[State], float], log_limit: int = 0) -> SearchResult:
    """Greedy best-first search: f = h. Fast, not optimal."""
    return best_first_search(problem, lambda g, s: heuristic(s), "Greedy", heuristic, log_limit)


def breadth_first_search(problem: Problem) -> SearchResult:
    """Breadth-first search: fewest steps, ignores cost. Optimal only when all steps cost the same."""
    start = problem.initial
    if problem.is_goal(start):
        return SearchResult("BFS", [], 0.0, 0, 0, 1)
    frontier: deque[State] = deque([start])
    parent: dict[State, tuple[State, str] | None] = {start: None}
    cost_to: dict[State, float] = {start: 0.0}
    expanded = generated = 0
    max_frontier = 1
    while frontier:
        state = frontier.popleft()
        expanded += 1
        for action, nxt, step_cost in problem.successors(state):
            if nxt in parent:
                continue
            parent[nxt] = (state, action)
            cost_to[nxt] = cost_to[state] + step_cost
            generated += 1
            if problem.is_goal(nxt):  # BFS may test at generation: the first goal found is the shallowest
                return SearchResult("BFS", _plan(parent, nxt), cost_to[nxt], expanded, generated, max_frontier)
            frontier.append(nxt)
        max_frontier = max(max_frontier, len(frontier))
    return SearchResult("BFS", [], float("inf"), expanded, generated, max_frontier)


def _plan(parent: dict, state: State) -> list[str]:
    actions: list[str] = []
    while parent[state] is not None:
        state, action = parent[state]
        actions.append(action)
    actions.reverse()
    return actions


@dataclass
class RouteProblem:
    """Find the cheapest order of skills to study to complete every target skill."""

    hard: dict[str, frozenset[str]]  # skill -> prerequisites that must be completed first
    soft: dict[str, frozenset[str]]  # skill -> prerequisites that only make it faster
    base_cost: dict[str, float]  # minutes for a skill when all its soft prerequisites are done
    completed: frozenset[str]
    targets: frozenset[str]
    soft_penalty: float = 0.4

    def __post_init__(self) -> None:
        self.initial: frozenset[str] = frozenset(self.completed)
        self.required = self._closure(follow_soft=False)  # must be studied on every route
        self.relevant = self._closure(follow_soft=True)  # may be worth studying
        self._order = sorted(self.relevant)
        self._required_order = sorted(self.required)  # a fixed order, so sums of floats do not depend on set hashing

    def _closure(self, follow_soft: bool) -> frozenset[str]:
        """Skills still to study to reach the targets, walking prerequisite edges backwards."""
        seen: set[str] = set()
        stack = [t for t in self.targets if t not in self.completed]
        while stack:
            skill = stack.pop()
            if skill in seen:
                continue
            seen.add(skill)
            parents = self.hard[skill] | (self.soft[skill] if follow_soft else frozenset())
            stack.extend(p for p in parents if p not in self.completed and p not in seen)
        return frozenset(seen)

    def is_goal(self, state: frozenset[str]) -> bool:
        return self.targets <= state

    def step_cost(self, skill: str, state: frozenset[str]) -> float:
        missing = sum(1 for p in self.soft[skill] if p not in state)
        return self.base_cost[skill] * (1.0 + self.soft_penalty * missing)

    def successors(self, state: frozenset[str]) -> Iterable[tuple[str, frozenset[str], float]]:
        for skill in self._order:
            if skill not in state and self.hard[skill] <= state:
                yield skill, state | {skill}, self.step_cost(skill, state)

    def heuristic(self, state: frozenset[str]) -> float:
        """h(state) = sum of the base costs of the required skills not yet completed.

        Admissible: every required skill must still be studied, and never for less than its
        base cost (penalties only add). Consistent: completing a skill lowers h by at most that
        skill's base cost, which is never more than the step cost actually paid.
        """
        return math.fsum(self.base_cost[skill] for skill in self._required_order if skill not in state)

    def route_cost(self, order: list[str]) -> float:
        """Cost of studying the skills in the given order (inf if a hard prerequisite is violated)."""
        state, total = self.initial, 0.0
        for skill in order:
            if not self.hard[skill] <= state:
                return float("inf")
            total += self.step_cost(skill, state)
            state = state | {skill}
        return total if self.is_goal(state) else float("inf")


def plan_route(problem: RouteProblem, log_limit: int = 60) -> SearchResult:
    return astar(problem, problem.heuristic, log_limit)

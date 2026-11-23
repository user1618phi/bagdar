"""Search: A* is checked against brute force, and the heuristic against its two definitions."""

import itertools
import random
import unittest

from meje import search
from meje.content import load_pack
from meje.tutor import Tutor


class Graph:
    """A small explicit weighted graph, for textbook-style checks."""

    def __init__(self, edges, start, goal):
        self.edges, self.initial, self.goal = edges, start, goal

    def is_goal(self, state):
        return state == self.goal

    def successors(self, state):
        for nxt, cost in sorted(self.edges.get(state, {}).items()):
            yield f"{state}->{nxt}", nxt, cost


GRAPH = {"S": {"A": 2, "B": 1}, "A": {"G": 6}, "B": {"C": 2}, "C": {"G": 3}}
H = {"S": 5, "A": 6, "B": 5, "C": 3, "G": 0}
MISLEADING = {"S": 5, "A": 1, "B": 5, "C": 5, "G": 0}


def random_route_problem(rng, size):
    names = [f"s{i}" for i in range(size)]
    hard, soft = {}, {}
    for i, name in enumerate(names):
        earlier = names[:i]
        hard[name] = frozenset(p for p in earlier if rng.random() < 0.3)
        soft[name] = frozenset(p for p in earlier if p not in hard[name] and rng.random() < 0.3)
    cost = {name: rng.uniform(0.5, 6.0) for name in names}
    targets = frozenset(rng.sample(names, rng.randint(1, 2)))
    completed = frozenset(n for n in names if not hard[n] and n not in targets and rng.random() < 0.15)
    return search.RouteProblem(hard, soft, cost, completed, targets, soft_penalty=rng.choice([0.0, 0.4, 1.0]))


def brute_force_route(problem):
    """Try every order of every subset of the relevant skills (exponential, tests only)."""
    best = float("inf")
    todo = sorted(problem.relevant)
    for size in range(len(todo) + 1):
        for subset in itertools.combinations(todo, size):
            for order in itertools.permutations(subset):
                best = min(best, problem.route_cost(list(order)))
    return best


class GenericSearchTests(unittest.TestCase):
    def test_astar_and_ucs_find_the_cheapest_path(self):
        problem = Graph(GRAPH, "S", "G")
        for result in (search.astar(problem, H.get), search.uniform_cost_search(problem)):
            self.assertEqual(result.actions, ["S->B", "B->C", "C->G"])
            self.assertAlmostEqual(result.cost, 6.0)

    def test_bfs_finds_the_fewest_steps_not_the_cheapest(self):
        result = search.breadth_first_search(Graph(GRAPH, "S", "G"))
        self.assertEqual(result.actions, ["S->A", "A->G"])
        self.assertAlmostEqual(result.cost, 8.0)

    def test_greedy_can_be_misled(self):
        result = search.greedy_best_first(Graph(GRAPH, "S", "G"), MISLEADING.get)
        self.assertAlmostEqual(result.cost, 8.0)

    def test_astar_stays_optimal_with_an_inconsistent_but_admissible_heuristic(self):
        result = search.astar(Graph(GRAPH, "S", "G"), {"S": 0, "A": 0, "B": 5, "C": 0, "G": 0}.get)
        self.assertAlmostEqual(result.cost, 6.0)

    def test_unreachable_goal_is_reported(self):
        result = search.astar(Graph({"S": {"A": 1}}, "S", "G"), lambda s: 0)
        self.assertFalse(result.found)
        self.assertEqual(result.actions, [])

    def test_start_is_goal(self):
        result = search.astar(Graph(GRAPH, "G", "G"), H.get)
        self.assertEqual((result.actions, result.cost, result.expanded), ([], 0.0, 0))

    def test_negative_costs_are_rejected(self):
        with self.assertRaises(ValueError):
            search.uniform_cost_search(Graph({"S": {"G": -1}}, "S", "G"))


class RouteProblemTests(unittest.TestCase):
    def test_astar_matches_brute_force_on_random_graphs(self):
        rng = random.Random(3)
        for _ in range(120):
            problem = random_route_problem(rng, rng.randint(2, 6))
            result = search.plan_route(problem)
            self.assertAlmostEqual(result.cost, brute_force_route(problem), places=9)
            self.assertAlmostEqual(problem.route_cost(result.actions), result.cost, places=9)

    def test_heuristic_is_admissible_and_consistent(self):
        rng = random.Random(11)
        for _ in range(40):
            problem = random_route_problem(rng, rng.randint(3, 7))
            states, stack = {problem.initial}, [problem.initial]
            while stack:
                state = stack.pop()
                for _, nxt, cost in problem.successors(state):
                    self.assertLessEqual(problem.heuristic(state), cost + problem.heuristic(nxt) + 1e-9)
                    if nxt not in states:
                        states.add(nxt)
                        stack.append(nxt)
            for state in states:
                rest = search.RouteProblem(problem.hard, problem.soft, problem.base_cost, state, problem.targets, problem.soft_penalty)
                true_cost = search.uniform_cost_search(rest).cost
                self.assertLessEqual(problem.heuristic(state), true_cost + 1e-9)
                if problem.is_goal(state):
                    self.assertEqual(problem.heuristic(state), 0.0)

    def test_routes_respect_hard_prerequisites(self):
        rng = random.Random(5)
        for _ in range(100):
            problem = random_route_problem(rng, rng.randint(3, 8))
            done = set(problem.completed)
            for skill in search.plan_route(problem).actions:
                self.assertTrue(problem.hard[skill] <= done)
                done.add(skill)
            self.assertTrue(problem.targets <= done)

    def test_soft_prerequisite_is_taken_only_when_it_pays_off(self):
        hard = {"basics": frozenset(), "goal": frozenset()}
        soft = {"basics": frozenset(), "goal": frozenset({"basics"})}
        targets = frozenset({"goal"})
        cheap = search.RouteProblem(hard, soft, {"basics": 1.0, "goal": 10.0}, frozenset(), targets, 0.4)
        self.assertEqual(search.plan_route(cheap).actions, ["basics", "goal"])
        costly = search.RouteProblem(hard, soft, {"basics": 6.0, "goal": 10.0}, frozenset(), targets, 0.4)
        self.assertEqual(search.plan_route(costly).actions, ["goal"])

    def test_completed_skills_are_not_studied_again(self):
        hard = {"a": frozenset(), "b": frozenset({"a"}), "c": frozenset({"b"})}
        soft = {k: frozenset() for k in hard}
        problem = search.RouteProblem(hard, soft, {"a": 1.0, "b": 1.0, "c": 1.0}, frozenset({"b"}), frozenset({"c"}))
        self.assertEqual(search.plan_route(problem).actions, ["c"])

    def test_on_the_course_astar_is_optimal_and_expands_fewer_states_than_ucs(self):
        tutor = Tutor(load_pack())
        beliefs = {sid: list(tutor.model.prior) for sid in tutor.pack.skills}
        for destination in tutor.pack.destinations:
            problem = tutor.route_problem(frozenset(), frozenset(destination["targets"]), beliefs)
            astar = search.plan_route(problem)
            ucs = search.uniform_cost_search(problem)
            self.assertAlmostEqual(astar.cost, ucs.cost, places=9)
            self.assertLessEqual(astar.expanded, ucs.expanded)
            self.assertGreaterEqual(search.breadth_first_search(problem).cost, ucs.cost - 1e-9)


if __name__ == "__main__":
    unittest.main()

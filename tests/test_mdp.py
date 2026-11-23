"""MDP: checked against closed-form solutions and the Bellman equation itself."""

import unittest

from meje import mdp
from meje.tutor import TutorModel


def toy_mdp(gamma=0.9):
    """Two states, two actions, small enough to solve on paper.

    'work' in LOW earns 1 and moves to HIGH with probability 0.5; in HIGH it earns 3 and stays.
    'rest' earns 0 and always leads to LOW.
    """
    return mdp.MDP(
        states=("low", "high"), actions=("work", "rest"),
        transitions={"work": [[0.5, 0.5], [0.0, 1.0]], "rest": [[1.0, 0.0], [1.0, 0.0]]},
        rewards={"work": [1.0, 3.0], "rest": [0.0, 0.0]},
        terminal_actions=frozenset(), gamma=gamma,
    )


class ValueIterationTests(unittest.TestCase):
    def test_toy_mdp_matches_the_closed_form(self):
        result = mdp.value_iteration(toy_mdp())
        v_high = 3.0 / (1 - 0.9)  # work forever in HIGH: 3 + 0.9 * V(high)
        v_low = (1.0 + 0.9 * 0.5 * v_high) / (1 - 0.9 * 0.5)  # 1 + 0.9 * (0.5 V(low) + 0.5 V(high))
        self.assertAlmostEqual(result.values[1], v_high, places=6)
        self.assertAlmostEqual(result.values[0], v_low, places=6)
        self.assertEqual(result.policy, ["work", "work"])

    def test_one_bellman_update_by_hand(self):
        # From V = [0, 0]: V1(low) = max(1 + 0, 0 + 0) = 1; V1(high) = max(3, 0) = 3.
        self.assertEqual(mdp.bellman_update(toy_mdp(), [0.0, 0.0]), [1.0, 3.0])
        # From V = [1, 3]: work in low = 1 + 0.9 * (0.5 * 1 + 0.5 * 3) = 2.8; rest = 0.9 * 1 = 0.9.
        self.assertAlmostEqual(mdp.bellman_update(toy_mdp(), [1.0, 3.0])[0], 2.8)

    def test_tutor_mdp_matches_the_closed_form(self):
        model = TutorModel()
        result = mdp.value_iteration(model.build_mdp())
        v_mastered = 10.0  # advance
        v_fragile = (-1 + 0.95 * 0.4 * v_mastered) / (1 - 0.95 * 0.6)  # practise until mastered
        v_unknown = (-2 + 0.95 * 0.65 * v_fragile) / (1 - 0.95 * 0.35)  # explain until fragile
        for got, want in zip(result.values, [v_unknown, v_fragile, v_mastered]):
            self.assertAlmostEqual(got, want, places=7)
        self.assertEqual(result.policy, ["explain", "practice", "advance"])

    def test_solution_satisfies_the_bellman_equation(self):
        problem = TutorModel().build_mdp()
        result = mdp.value_iteration(problem)
        for got, want in zip(mdp.bellman_update(problem, result.values), result.values):
            self.assertAlmostEqual(got, want, places=8)

    def test_residual_shrinks_at_least_by_gamma(self):
        """The Bellman update is a gamma-contraction in the max norm."""
        for problem in (toy_mdp(), TutorModel().build_mdp()):
            residuals = [residual for _, residual in mdp.value_iteration(problem).history]
            for previous, current in zip(residuals, residuals[1:]):
                self.assertLessEqual(current, problem.gamma * previous + 1e-12)

    def test_policy_is_greedy_with_respect_to_q(self):
        result = mdp.value_iteration(TutorModel().build_mdp())
        for state, action in enumerate(result.policy):
            self.assertEqual(result.q[action][state], max(result.q[a][state] for a in result.q))

    def test_gamma_one_is_rejected(self):
        with self.assertRaises(ValueError):
            mdp.value_iteration(toy_mdp(gamma=1.0))

    def test_broken_transition_table_is_rejected(self):
        broken = mdp.MDP(("a",), ("go",), {"go": [[0.7]]}, {"go": [0.0]}, frozenset(), 0.9)
        with self.assertRaises(ValueError):
            mdp.value_iteration(broken)


class PolicyTests(unittest.TestCase):
    def test_expected_minutes_match_the_closed_form(self):
        model = TutorModel()
        problem = model.build_mdp()
        policy = mdp.value_iteration(problem).policy
        minutes = mdp.expected_cost_to_finish(problem, policy, dict(model.minutes))
        fragile = 1 / 0.4  # geometric: each question masters with probability 0.4
        unknown = (2 + 0.65 * fragile) / 0.65
        self.assertAlmostEqual(minutes[2], 0.0)
        self.assertAlmostEqual(minutes[1], fragile, places=8)
        self.assertAlmostEqual(minutes[0], unknown, places=8)

    def test_qmdp_is_the_expectation_of_q(self):
        result = mdp.value_iteration(TutorModel().build_mdp())
        for state in range(3):
            one_hot = [1.0 if s == state else 0.0 for s in range(3)]
            values = mdp.qmdp_values(result.q, one_hot)
            for action in result.q:
                self.assertAlmostEqual(values[action], result.q[action][state])
        mixed = mdp.qmdp_values(result.q, [0.5, 0.3, 0.2])
        self.assertAlmostEqual(mixed["advance"], 0.5 * -15 + 0.3 * -5 + 0.2 * 10)

    def test_greedy_tie_break_is_deterministic(self):
        self.assertEqual(mdp.greedy_action({"explain": 1.0, "practice": 1.0, "advance": 0.0}), "explain")


if __name__ == "__main__":
    unittest.main()

"""Experiments: reproducible, and the claims made in the report hold on a small run."""

import random
import unittest

from bagdar import simulate
from bagdar.content import load_pack
from bagdar.tutor import Tutor

TUTOR = Tutor(load_pack())


class SimulationTests(unittest.TestCase):
    def test_same_seed_gives_the_same_numbers(self):
        learner = simulate.HmmLearner(TUTOR.model)
        first = simulate.compare_policies(TUTOR, learner, episodes=300, seed=3)
        second = simulate.compare_policies(TUTOR, learner, episodes=300, seed=3)
        self.assertEqual(first, second)

    def test_tutor_beats_the_baselines_and_stays_below_the_oracle(self):
        for build in simulate.LEARNERS.values():
            rows = {row["policy"]: row for row in simulate.compare_policies(TUTOR, build(TUTOR), episodes=3000, seed=5)}
            tutor = rows["Bagdar (HMM + MDP)"]["payoff"]
            self.assertGreater(tutor, rows["Fixed dose"]["payoff"])
            self.assertGreater(tutor, rows["Lessons only"]["payoff"])
            self.assertGreater(tutor, rows["3-in-a-row"]["payoff"])
            self.assertLess(tutor, rows["Oracle (sees truth)"]["payoff"])

    def test_forecasts_are_calibrated_when_the_model_is_right(self):
        result = simulate.calibration(TUTOR, simulate.HmmLearner(TUTOR.model), episodes=4000, seed=1)
        self.assertLess(result["expected_calibration_error"], 0.02)
        self.assertLess(result["brier"], result["brier_base_rate"])

    def test_every_episode_ends(self):
        rng = random.Random(0)
        for build in simulate.LEARNERS.values():
            for policy in simulate.make_policies(TUTOR).values():
                for _ in range(50):
                    run = simulate.run_episode(TUTOR, build(TUTOR), policy, rng)
                    self.assertIn(run["state"], (0, 1, 2))
                    self.assertLessEqual(run["minutes"], 120)

    def test_astar_is_always_optimal_in_the_search_experiment(self):
        for row in simulate.compare_search(TUTOR, profiles=15, seed=2):
            by = {a["algorithm"]: a for a in row["algorithms"]}
            self.assertEqual(by["A*"]["optimal_share"], 1.0)
            self.assertAlmostEqual(by["A*"]["cost_ratio"], 1.0)
            self.assertLessEqual(by["A*"]["expanded"], by["UCS"]["expanded"])


if __name__ == "__main__":
    unittest.main()

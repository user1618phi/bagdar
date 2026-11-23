"""Learning from data: Baum-Welch and the scoring functions, checked on data with a known answer."""

import random
import unittest

from bagdar import realdata
from bagdar.realdata import BinaryHMM


def sample_sequences(model, students, length, seed):
    """Draw answer sequences from a known HMM, so the fit can be compared with the truth."""
    rng = random.Random(seed)

    def draw(distribution):
        threshold, total = rng.random(), 0.0
        for index, p in enumerate(distribution):
            total += p
            if threshold < total:
                return index
        return len(distribution) - 1

    sequences = {}
    for student in range(students):
        state, answers = draw(model.prior), []
        for _ in range(length):
            answers.append(int(rng.random() < model.p_correct[state]))
            state = draw(model.transition[state])
        sequences[(str(student), "skill")] = answers
    return sequences


TRUTH = BinaryHMM([0.6, 0.4], [[0.85, 0.15], [0.0, 1.0]], [0.2, 0.9])


class BaumWelchTests(unittest.TestCase):
    def test_recovers_known_parameters(self):
        data = sample_sequences(TRUTH, students=3000, length=12, seed=1)
        start = BinaryHMM([0.5, 0.5], [[0.7, 0.3], [0.0, 1.0]], [0.35, 0.75])
        fitted, _ = realdata.baum_welch(data, start, iterations=60)
        self.assertAlmostEqual(fitted.p_correct[0], 0.2, delta=0.03)
        self.assertAlmostEqual(fitted.p_correct[1], 0.9, delta=0.03)
        self.assertAlmostEqual(fitted.transition[0][1], 0.15, delta=0.03)
        self.assertAlmostEqual(fitted.prior[0], 0.6, delta=0.05)

    def test_likelihood_never_decreases(self):
        """The defining property of expectation-maximisation."""
        data = sample_sequences(TRUTH, students=400, length=10, seed=2)
        _, history = realdata.baum_welch(data, BinaryHMM([0.5, 0.5], [[0.6, 0.4], [0.0, 1.0]], [0.4, 0.7]), iterations=25, tolerance=0.0)
        for previous, current in zip(history, history[1:]):
            self.assertGreaterEqual(current, previous - 1e-9)

    def test_structure_is_preserved(self):
        data = sample_sequences(TRUTH, students=300, length=8, seed=3)
        fitted, _ = realdata.baum_welch(data, BinaryHMM([0.5, 0.5], [[0.6, 0.4], [0.0, 1.0]], [0.4, 0.7]), iterations=10)
        self.assertEqual(fitted.transition[1], [0.0, 1.0])  # knowledge never moves backwards
        self.assertAlmostEqual(sum(fitted.prior), 1.0)
        self.assertAlmostEqual(sum(fitted.transition[0]), 1.0)

    def test_per_skill_prior_separates_easy_and_hard_skills(self):
        easy = BinaryHMM([0.1, 0.9], TRUTH.transition, TRUTH.p_correct)
        hard = BinaryHMM([0.9, 0.1], TRUTH.transition, TRUTH.p_correct)
        data = {(u, "easy"): a for (u, _), a in sample_sequences(easy, 500, 8, 4).items()}
        data.update({(u, "hard"): a for (u, _), a in sample_sequences(hard, 500, 8, 5).items()})
        fitted, _ = realdata.baum_welch(data, TRUTH, iterations=15, per_skill_prior=True)
        self.assertGreater(fitted.skill_prior["easy"][1], fitted.skill_prior["hard"][1] + 0.4)


class ForecastTests(unittest.TestCase):
    def test_first_forecast_is_the_prior_expectation(self):
        forecasts = TRUTH.forecast("skill", [1, 1, 0])
        self.assertAlmostEqual(forecasts[0], 0.6 * 0.2 + 0.4 * 0.9)
        self.assertGreater(forecasts[1], forecasts[0])  # a correct answer raises the next forecast
        self.assertEqual(len(forecasts), 3)

    def test_auc(self):
        self.assertAlmostEqual(realdata.auc([(0.1, 0), (0.4, 0), (0.35, 1), (0.8, 1)]), 0.75)  # textbook example
        self.assertAlmostEqual(realdata.auc([(0.2, 0), (0.9, 1)]), 1.0)
        self.assertAlmostEqual(realdata.auc([(0.5, 0), (0.5, 1), (0.5, 0), (0.5, 1)]), 0.5)  # ties count half

    def test_degenerate_inputs_do_not_crash(self):
        self.assertEqual(realdata.auc([(0.3, 1), (0.9, 1)]), 0.5)  # one class: no ranking information
        data = {("1", "skill"): [], ("2", "skill"): [1, 0, 1]}
        fitted, history = realdata.baum_welch(data, TRUTH, iterations=2)
        self.assertEqual(len(history), 2)
        self.assertAlmostEqual(sum(fitted.prior), 1.0)

    def test_score_of_perfect_and_constant_forecasts(self):
        perfect = realdata.score([(1.0, 1), (0.0, 0), (1.0, 1), (0.0, 0)])
        self.assertAlmostEqual(perfect["brier"], 0.0)
        self.assertEqual(perfect["accuracy"], 1.0)
        constant = realdata.score([(0.5, 1), (0.5, 0)])
        self.assertAlmostEqual(constant["brier"], 0.25)
        self.assertAlmostEqual(constant["calibration_error"], 0.0)

    def test_split_keeps_each_student_on_one_side(self):
        data = {(str(u), s): [1] for u in range(200) for s in ("a", "b")}
        train, test = realdata.split_by_student(data)
        self.assertFalse({u for u, _ in train} & {u for u, _ in test})
        self.assertTrue(20 < len({u for u, _ in test}) < 60)


if __name__ == "__main__":
    unittest.main()

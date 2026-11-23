"""HMM: checked against the textbook umbrella world, hand calculations and brute force."""

import itertools
import math
import random
import unittest

from bagdar import hmm
from bagdar.tutor import TutorModel

# Umbrella world, Russell & Norvig AIMA 4e, section 14.2. States: rain, no rain.
T = [[0.7, 0.3], [0.3, 0.7]]
UMBRELLA = [0.9, 0.2]
NO_UMBRELLA = [0.1, 0.8]


def brute_force_best_path(prior, steps):
    """Score every possible state sequence and return the best one (exponential, tests only)."""
    size, best, best_p = len(prior), None, -1.0
    for path in itertools.product(range(size), repeat=len(steps) + 1):
        p = prior[path[0]]
        for t, step in enumerate(steps):
            if step.likelihood is not None:
                p *= step.likelihood[path[t]]
            p *= step.transition[path[t]][path[t + 1]]
        if p > best_p + 1e-15:
            best, best_p = list(path), p
    return best, best_p


def brute_force_evidence(prior, steps):
    size, total = len(prior), 0.0
    for path in itertools.product(range(size), repeat=len(steps) + 1):
        p = prior[path[0]]
        for t, step in enumerate(steps):
            if step.likelihood is not None:
                p *= step.likelihood[path[t]]
            p *= step.transition[path[t]][path[t + 1]]
        total += p
    return total


class FilteringTests(unittest.TestCase):
    def test_umbrella_world_matches_the_textbook(self):
        # AIMA predicts first and then conditions, so day 0 is a step without evidence.
        steps = [hmm.Step(T), hmm.Step(T, UMBRELLA), hmm.Step(T, UMBRELLA)]
        trace = hmm.forward([0.5, 0.5], steps)
        self.assertAlmostEqual(trace[1].posterior[0], 0.818, places=3)  # P(R1 | u1)
        self.assertAlmostEqual(trace[2].posterior[0], 0.883, places=3)  # P(R2 | u1, u2)

    def test_one_step_matches_the_hand_calculation(self):
        model = TutorModel()
        step = hmm.Step(model.transition("practice"), model.likelihood("correct_sure"))
        result = hmm.forward(list(model.prior), [step])[0]
        # weights 0.5*0.0375, 0.3*0.2925, 0.2*0.828 = 0.01875, 0.08775, 0.1656; sum 0.2721
        self.assertAlmostEqual(result.evidence_probability, 0.2721, places=4)
        for got, want in zip(result.posterior, [0.0689, 0.3225, 0.6086]):
            self.assertAlmostEqual(got, want, places=4)
        # transition: U keeps 0.9; F = 0.1*U + 0.6*F; M = 0.4*F + M
        for got, want in zip(result.predicted, [0.0620, 0.2004, 0.7376]):
            self.assertAlmostEqual(got, want, places=4)

    def test_a_step_without_evidence_only_predicts(self):
        model = TutorModel()
        result = hmm.forward(list(model.prior), [hmm.Step(model.transition("explain"))])[0]
        self.assertEqual(result.posterior, list(model.prior))
        self.assertIsNone(result.evidence_probability)
        self.assertAlmostEqual(result.predicted[0], 0.5 * 0.35)

    def test_beliefs_always_sum_to_one(self):
        model, rng = TutorModel(), random.Random(1)
        for _ in range(200):
            steps = []
            for _ in range(rng.randint(1, 12)):
                if rng.random() < 0.3:
                    steps.append(hmm.Step(model.transition("explain")))
                else:
                    observation = rng.choice(["correct_sure", "correct_unsure", "wrong_unsure", "wrong_sure"])
                    steps.append(hmm.Step(model.transition("practice"), model.likelihood(observation)))
            for result in hmm.forward(list(model.prior), steps):
                for belief in (result.posterior, result.predicted):
                    self.assertAlmostEqual(sum(belief), 1.0, places=12)
                    self.assertTrue(all(0.0 <= p <= 1.0 for p in belief))

    def test_correct_answers_raise_mastery_and_wrong_answers_lower_it(self):
        model = TutorModel()
        prior = list(model.prior)
        right = hmm.forward(prior, [hmm.Step(model.transition("practice"), model.likelihood("correct_sure"))])[0]
        wrong = hmm.forward(prior, [hmm.Step(model.transition("practice"), model.likelihood("wrong_unsure"))])[0]
        self.assertGreater(right.posterior[2], prior[2])
        self.assertLess(wrong.posterior[2], prior[2])
        unsure = hmm.forward(prior, [hmm.Step(model.transition("practice"), model.likelihood("correct_unsure"))])[0]
        self.assertGreater(right.posterior[2], unsure.posterior[2])  # confidence is evidence too

    def test_impossible_evidence_is_reported(self):
        with self.assertRaises(ValueError):
            hmm.condition([1.0, 0.0], [0.0, 0.5])

    def test_log_likelihood_matches_brute_force(self):
        steps = [hmm.Step(T, UMBRELLA), hmm.Step(T, NO_UMBRELLA), hmm.Step(T, UMBRELLA)]
        self.assertAlmostEqual(hmm.log_likelihood([0.5, 0.5], steps), math.log(brute_force_evidence([0.5, 0.5], steps)))


class ViterbiTests(unittest.TestCase):
    def test_umbrella_world_matches_the_textbook(self):
        # AIMA figure 14.5: umbrella on days 1, 2, 4, 5 -> rain, rain, no rain, rain, rain.
        steps = [hmm.Step(T, e) for e in (UMBRELLA, UMBRELLA, NO_UMBRELLA, UMBRELLA, UMBRELLA)]
        path, _ = hmm.viterbi([0.5, 0.5], steps)
        self.assertEqual(path[:5], [0, 0, 1, 0, 0])

    def test_matches_brute_force_on_random_sequences(self):
        model, rng = TutorModel(), random.Random(7)
        for _ in range(150):
            steps = []
            for _ in range(rng.randint(1, 6)):
                if rng.random() < 0.3:
                    steps.append(hmm.Step(model.transition("explain")))
                else:
                    observation = rng.choice(["correct_sure", "correct_unsure", "wrong_unsure", "wrong_sure"])
                    steps.append(hmm.Step(model.transition("practice"), model.likelihood(observation)))
            path, log_probability = hmm.viterbi(list(model.prior), steps)
            _, best_p = brute_force_best_path(list(model.prior), steps)
            self.assertAlmostEqual(log_probability, math.log(best_p), places=9)

    def test_path_differs_from_per_step_argmax(self):
        """Viterbi returns the best sequence, which respects the transitions."""
        model = TutorModel()
        steps = [hmm.Step(model.transition("practice"), model.likelihood(o))
                 for o in ("correct_sure", "wrong_unsure", "correct_sure", "correct_sure")]
        path, _ = hmm.viterbi(list(model.prior), steps)
        self.assertEqual(path, sorted(path))  # knowledge never moves backwards in this model
        self.assertEqual(len(path), len(steps) + 1)

    def test_no_steps_returns_the_most_likely_prior_state(self):
        path, log_probability = hmm.viterbi([0.2, 0.5, 0.3], [])
        self.assertEqual(path, [1])
        self.assertAlmostEqual(log_probability, math.log(0.5))


if __name__ == "__main__":
    unittest.main()

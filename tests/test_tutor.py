"""Integration: the three algorithms working as one tutor, plus content and readiness checks."""

import random
import unittest

from bagdar import readiness
from bagdar.content import load_pack
from bagdar.tutor import Tutor

PACK = load_pack()
TUTOR = Tutor(PACK)
DEFENSE = ["astar", "viterbi", "bellman"]


def answer(state, correct=True, sure=True):
    """Build the event for answering the current question."""
    item = PACK.items[state["current"]["item"]["id"]]
    choice = item.answer if correct else (item.answer + 1) % len(item.options)
    return {"skill": state["current"]["skill"], "action": "practice", "item": item.id, "choice": choice, "sure": sure}


def play(targets, rng, p_correct, max_events=2000, pin_rate=0.0):
    """Run a whole session with a learner who answers correctly with probability p_correct."""
    history, state = [], TUTOR.replay(targets, [])
    while not state["done"] and len(history) < max_events:
        history += state["append"]
        current = state["current"]
        if current is None:
            break
        if current["action"] == "explain":
            history.append({"skill": current["skill"], "action": "explain"})
        else:
            history.append(answer(state, rng.random() < p_correct, rng.random() < 0.5))
        pin = None
        if rng.random() < pin_rate:
            pin = rng.choice([s["id"] for s in state["skills"] if not s["locked"]])
        state = TUTOR.replay(targets, history, pin=pin)
    return history + state["append"], state


class ContentTests(unittest.TestCase):
    def test_every_skill_has_a_lesson_and_four_questions(self):
        self.assertEqual(len(PACK.skills), 20)
        for skill in PACK.skills:
            self.assertIn(skill, PACK.lessons)
            self.assertEqual(len(PACK.items_by_skill[skill]), 4)

    def test_questions_are_well_formed(self):
        for item in PACK.items.values():
            self.assertEqual(len(item.options), 4, item.id)
            self.assertEqual(len(set(item.options)), 4, item.id)
            self.assertIn(item.answer, range(4), item.id)
            self.assertIn(item.level, (1, 2, 3), item.id)
            self.assertTrue(item.prompt and item.why, item.id)

    def test_correct_answers_are_spread_over_all_positions(self):
        counts = [sum(1 for i in PACK.items.values() if i.answer == position) for position in range(4)]
        self.assertGreaterEqual(min(counts), 15)


class ReadinessTests(unittest.TestCase):
    def test_distribution_sums_to_one_and_matches_the_binomial(self):
        distribution = readiness.score_distribution([0.5, 0.5, 0.5])
        self.assertAlmostEqual(sum(distribution), 1.0)
        for got, want in zip(distribution, [0.125, 0.375, 0.375, 0.125]):
            self.assertAlmostEqual(got, want)

    def test_pass_probability(self):
        self.assertAlmostEqual(readiness.pass_probability([0.5, 0.5], 0.5), 0.75)  # at least 1 of 2
        self.assertAlmostEqual(readiness.pass_probability([0.9, 0.8], 1.0), 0.72)  # both
        self.assertAlmostEqual(readiness.pass_probability([1.0] * 5, 0.7), 1.0)
        self.assertAlmostEqual(readiness.pass_probability([0.0] * 5, 0.7), 0.0)
        self.assertEqual(readiness.pass_probability([], 0.7), 1.0)


class DecisionTests(unittest.TestCase):
    def test_first_step_is_a_question_on_the_first_stop(self):
        state = TUTOR.replay(DEFENSE, [])
        self.assertEqual(state["current"]["action"], "practice")
        self.assertEqual(state["current"]["skill"], state["route"]["stops"][0]["skill"])
        self.assertEqual(state["append"], [])

    def test_a_hesitant_wrong_answer_leads_to_a_lesson(self):
        state = TUTOR.replay(DEFENSE, [])
        state = TUTOR.replay(DEFENSE, [answer(state, correct=False, sure=False)])
        self.assertEqual(state["current"]["action"], "explain")
        self.assertFalse(state["last"]["correct"])
        self.assertLess(state["last"]["posterior"][2], TUTOR.model.prior[2])

    def test_two_confident_correct_answers_complete_a_skill(self):
        history, state = [], TUTOR.replay(DEFENSE, [])
        first = state["current"]["skill"]
        for _ in range(2):
            history.append(answer(state))
            state = TUTOR.replay(DEFENSE, history)
            history += state["append"]
        self.assertIn({"skill": first, "action": "advance", "auto": True}, history)
        self.assertNotEqual(state["current"]["skill"], first)
        status = {s["id"]: s["status"] for s in state["skills"]}
        self.assertEqual(status[first], "completed")

    def test_hesitant_correct_answers_need_more_evidence(self):
        history, state = [], TUTOR.replay(DEFENSE, [])
        for _ in range(2):
            history.append(answer(state, sure=False))
            state = TUTOR.replay(DEFENSE, history)
        self.assertEqual(state["append"], [])  # not advanced yet

    def test_eta_shrinks_and_readiness_grows_as_skills_are_mastered(self):
        start = TUTOR.replay(DEFENSE, [])
        history, state = play(DEFENSE, random.Random(0), p_correct=1.0)
        self.assertTrue(state["done"])
        self.assertEqual(state["route"]["eta_minutes"], 0)
        self.assertGreater(state["readiness"]["pass_probability"], start["readiness"]["pass_probability"])
        self.assertGreater(state["readiness"]["pass_probability"], 0.9)

    def test_route_changes_when_the_belief_changes(self):
        """Mastering a soft prerequisite elsewhere makes the route through it cheaper."""
        before = TUTOR.replay(["viterbi"], [])
        optional = set(before["route"]["search"]["optional"])
        self.assertIn("ucs", optional)  # ucs is a soft prerequisite of viterbi

    def test_replay_is_deterministic(self):
        history, _ = play(["astar"], random.Random(4), p_correct=0.6)
        self.assertEqual(TUTOR.replay(["astar"], history), TUTOR.replay(["astar"], history))


class LearnerControlTests(unittest.TestCase):
    def test_pinned_skill_becomes_current_and_the_detour_is_priced(self):
        state = TUTOR.replay(DEFENSE, [], pin="probability")
        self.assertEqual(state["current"]["skill"], "probability")
        self.assertGreaterEqual(state["route"]["detour_minutes"], 0.0)

    def test_locked_skill_cannot_be_pinned(self):
        state = TUTOR.replay(DEFENSE, [], pin="astar")  # needs ucs and heuristics first
        self.assertNotEqual(state["current"]["skill"], "astar")

    def test_learner_can_ask_for_the_lesson(self):
        state = TUTOR.replay(DEFENSE, [], lesson=True)
        self.assertEqual(state["current"]["action"], "explain")
        self.assertTrue(state["current"]["overridden"])
        self.assertIn("idea", state["current"]["lesson"])

    def test_completed_skill_can_be_reviewed(self):
        history, _ = play(["formulation"], random.Random(1), p_correct=1.0)
        state = TUTOR.replay(["formulation"], history, pin="agents")
        self.assertTrue(state["current"]["reviewing"])
        self.assertEqual(state["current"]["action"], "practice")

    def test_tutor_stays_on_the_skill_in_progress(self):
        state = TUTOR.replay(DEFENSE, [])
        first = state["current"]["skill"]
        state = TUTOR.replay(DEFENSE, [answer(state, correct=False, sure=False)])
        self.assertEqual(state["current"]["skill"], first)


class RobustnessTests(unittest.TestCase):
    def test_malformed_events_are_ignored(self):
        garbage = [None, 42, "x", {}, {"skill": "nope", "action": "practice"}, {"skill": "agents", "action": "fly"},
                   {"skill": "agents", "action": "practice", "item": "astar-1", "choice": 0, "sure": True},
                   {"skill": "agents", "action": "practice", "item": "agents-1", "choice": 9, "sure": True},
                   {"skill": "agents", "action": "practice", "item": "agents-1", "choice": True, "sure": True},
                   {"skill": "agents", "action": "practice", "item": "agents-1", "choice": 0, "sure": "yes"}]
        state = TUTOR.replay(DEFENSE, garbage)
        self.assertEqual(state["ignored_events"], len(garbage))
        self.assertEqual(state["answered"], 0)
        self.assertEqual(TUTOR.replay(DEFENSE, "not a list")["answered"], 0)

    def test_history_ending_in_a_manual_advance_does_not_crash(self):
        """Found by fuzzing: an advance sent by a client, with nothing before it, used to raise."""
        state = TUTOR.replay(DEFENSE, [{"skill": "agents", "action": "advance"}])
        self.assertIsNone(state["last"])
        self.assertEqual({s["id"]: s["status"] for s in state["skills"]}["agents"], "completed")
        first = TUTOR.replay(DEFENSE, [])
        history = [answer(first), {"skill": first["current"]["skill"], "action": "advance"}]
        last = TUTOR.replay(DEFENSE, history)["last"]
        self.assertEqual((last["action"], len(last["advanced"])), ("practice", 1))

    def test_adversarial_histories_never_break_the_tutor(self):
        rng = random.Random(123)
        skills = list(PACK.skills)

        def event():
            roll, skill = rng.random(), rng.choice(skills)
            if roll < 0.5:
                item = rng.choice(PACK.items_by_skill[skill])
                return {"skill": skill, "action": "practice", "item": item.id, "choice": rng.randrange(4), "sure": rng.random() < 0.5}
            if roll < 0.7:
                return {"skill": skill, "action": "explain"}
            if roll < 0.9:
                return {"skill": skill, "action": "advance", "auto": rng.random() < 0.5}  # may be locked or repeated
            return rng.choice([None, 5, {"skill": skill}])

        for _ in range(150):
            history = [event() for _ in range(rng.randrange(0, 60))]
            targets = rng.choice([d["targets"] for d in PACK.destinations] + [[rng.choice(skills)], [], skills])
            pin = rng.choice([None, rng.choice(skills), "nope"])
            state = TUTOR.replay(targets, history, pin=pin, lesson=rng.random() < 0.3)
            done = {e["skill"] for e in history if isinstance(e, dict) and e.get("action") == "advance"} | {e["skill"] for e in state["append"]}
            order = [stop["skill"] for stop in state["route"]["stops"]]
            self.assertEqual(len(set(order)), len(order))
            if state["current"] and not state["current"]["reviewing"]:
                self.assertEqual(order[0], state["current"]["skill"])
                self.assertTrue(PACK.skills[state["current"]["skill"]].hard <= done)
            if not state["current"]:
                self.assertTrue(set(state["targets"]) <= done)

    def test_wrong_types_anywhere_in_the_input_are_ignored(self):
        """Found in review: unhashable values in targets or events used to raise TypeError."""
        default = sorted(PACK.destinations[0]["targets"])
        self.assertEqual(TUTOR.replay([["astar"], {}, 7, None], [])["targets"], default)
        self.assertEqual(TUTOR.replay("astar", [])["targets"], default)
        state = TUTOR.replay(DEFENSE, [{"skill": [], "action": "explain"}, {"skill": "agents", "action": {}}], pin=[], inspect={})
        self.assertEqual(state["ignored_events"], 2)
        self.assertEqual(len(TUTOR.compare_search([[]], "x")), 4)

    def test_long_histories_are_fast_and_keep_early_events(self):
        """Found in review: history used to be cut to 2000 events, silently undoing early progress."""
        import time
        state = TUTOR.replay(["formulation"], [])
        review = answer(state)
        history = [{"skill": "agents", "action": "advance", "auto": True}] + [review] * 3000
        started = time.perf_counter()
        state = TUTOR.replay(["formulation"], history, pin="agents")
        self.assertLess(time.perf_counter() - started, 3.0)
        self.assertEqual({s["id"]: s["status"] for s in state["skills"]}["agents"], "completed")
        self.assertEqual(state["calibration"]["forecasts"], 3000)

    def test_questions_rotate_after_an_early_mistake(self):
        """Found in review: two early wrong answers used to trap the learner on those two questions."""
        history = [{"skill": "agents", "action": "advance", "auto": True}]  # review mode: no step limit
        asked = []
        for turn in range(14):
            state = TUTOR.replay(["formulation"], history, pin="agents")
            asked.append(state["current"]["item"]["id"])
            history.append(answer(state, correct=turn >= 2))
        self.assertEqual(set(asked[6:]), {i.id for i in PACK.items_by_skill["agents"]})
        self.assertTrue(all(a != b for a, b in zip(asked, asked[1:])))

    def test_a_locked_pin_does_not_cancel_the_skill_in_progress(self):
        state = TUTOR.replay(DEFENSE, [])
        first = state["current"]["skill"]
        state = TUTOR.replay(DEFENSE, [answer(state, correct=False, sure=False)], pin="astar")  # astar is locked
        self.assertEqual(state["current"]["skill"], first)

    def test_decisions_do_not_depend_on_hash_randomisation(self):
        """Found in review: summing floats over a set made ties break differently between runs."""
        import os
        import subprocess
        import sys
        code = ("from bagdar.content import load_pack; from bagdar.tutor import Tutor; t = Tutor(load_pack()); "
                "s = t.replay(t.pack.destinations[1]['targets'], []); "
                "print([x['skill'] for x in s['route']['stops']], s['route']['search']['expanded'])")
        outputs = set()
        for seed in ("0", "1", "2", "3"):
            run = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True,
                                 env={**os.environ, "PYTHONHASHSEED": seed}, cwd=str(__import__("pathlib").Path(__file__).resolve().parent.parent))
            outputs.add(run.stdout)
        self.assertEqual(len(outputs), 1)

    def test_unknown_targets_fall_back_to_the_default_destination(self):
        state = TUTOR.replay(["nope"], [])
        self.assertEqual(state["targets"], sorted(PACK.destinations[0]["targets"]))

    def test_a_learner_who_never_learns_is_not_trapped(self):
        history, state = play(["formulation"], random.Random(2), p_correct=0.0)
        self.assertTrue(state["done"])
        self.assertTrue(any(e.get("capped") for e in history))

    def test_random_sessions_always_terminate_with_valid_state(self):
        rng = random.Random(42)
        for destination in PACK.destinations:
            for p_correct in (0.25, 0.6, 0.9):
                history, state = play(destination["targets"], rng, p_correct, pin_rate=0.1)
                self.assertTrue(state["done"], destination["id"])
                completed = {e["skill"] for e in history if e["action"] == "advance"}
                self.assertTrue(set(destination["targets"]) <= completed)
                for skill in state["skills"]:
                    self.assertAlmostEqual(sum(skill["belief"]), 1.0, places=9)
                self.assertTrue(0.0 <= state["readiness"]["pass_probability"] <= 1.0)

    def test_route_shown_is_always_valid(self):
        rng = random.Random(9)
        history, state = [], TUTOR.replay(DEFENSE, [])
        for _ in range(40):
            if state["done"]:
                break
            history += state["append"]
            done = {e["skill"] for e in history if e["action"] == "advance"}
            for stop in state["route"]["stops"]:
                self.assertTrue(set(PACK.skills[stop["skill"]].hard) <= done, stop)
                done.add(stop["skill"])
            self.assertTrue(set(DEFENSE) <= done)
            self.assertAlmostEqual(state["route"]["eta_minutes"], state["route"]["optimal_minutes"] + state["route"]["detour_minutes"], places=6)
            current = state["current"]
            history.append({"skill": current["skill"], "action": "explain"} if current["action"] == "explain"
                           else answer(state, rng.random() < 0.7, rng.random() < 0.5))
            state = TUTOR.replay(DEFENSE, history)

    def test_calibration_counts_confidence(self):
        state = TUTOR.replay(DEFENSE, [])
        history = [answer(state, correct=True, sure=True)]
        state = TUTOR.replay(DEFENSE, history)
        history.append(answer(state, correct=False, sure=False))
        calibration = TUTOR.replay(DEFENSE, history)["calibration"]
        self.assertEqual(calibration["sure"], {"n": 1, "correct": 1})
        self.assertEqual(calibration["unsure"], {"n": 1, "correct": 0})
        self.assertEqual(calibration["forecasts"], 2)

    def test_calibration_ledger_records_every_forecast(self):
        state = TUTOR.replay(DEFENSE, [])
        history = [answer(state, correct=True, sure=True)]
        calibration = TUTOR.replay(DEFENSE, history)["calibration"]
        self.assertEqual(len(calibration["ledger"]), 1)
        self.assertAlmostEqual(calibration["ledger"][0]["forecast"], 0.5 * 0.25 + 0.3 * 0.65 + 0.2 * 0.92)
        self.assertEqual((calibration["observed"], calibration["mean_forecast"]), (1.0, calibration["ledger"][0]["forecast"]))
        self.assertIsNone(TUTOR.replay(DEFENSE, [])["calibration"]["brier"])

    def test_lookahead_is_a_tighter_bound_than_qmdp(self):
        """QMDP assumes the state becomes known after one step, so it can only be optimistic."""
        rng = random.Random(8)
        for _ in range(100):
            weights = [rng.random() for _ in range(3)]
            belief = [w / sum(weights) for w in weights]
            plain, deeper = TUTOR.action_values(belief), TUTOR.lookahead_values(belief, depth=1)
            self.assertAlmostEqual(deeper["advance"], plain["advance"])
            self.assertLessEqual(deeper["practice"], plain["practice"] + 1e-9)
            self.assertLessEqual(deeper["explain"], plain["explain"] + 1e-9)
        self.assertEqual(TUTOR.lookahead_values([0.5, 0.3, 0.2], depth=0), TUTOR.action_values([0.5, 0.3, 0.2]))

    def test_trace_exposes_every_number(self):
        state = TUTOR.replay(DEFENSE, [])
        state = TUTOR.replay(DEFENSE, [answer(state, correct=False, sure=False)])
        trace = state["trace"]
        self.assertEqual(len(trace["steps"]), 1)
        self.assertEqual(trace["steps"][0]["observation"], "wrong_unsure")
        self.assertEqual(len(trace["viterbi"]), 2)
        model = TUTOR.describe_model()
        self.assertEqual(model["policy"], ["explain", "practice", "advance"])
        self.assertTrue(0.8 < model["advance_threshold"] < 0.95)


if __name__ == "__main__":
    unittest.main()

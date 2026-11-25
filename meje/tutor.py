"""The tutor: three algorithms working on one problem.

    HMM   answers "where is the learner?"      belief over {unknown, fragile, mastered} per skill
    MDP   answers "what should happen next?"   explain, practice or advance, by expected value
    A*    answers "which skill comes next?"    cheapest route through the prerequisite graph

They are chained, not merely placed side by side:

    answers -> HMM belief -> MDP: Q(belief, action)            (QMDP rule)
                          -> A* step cost = belief . minutes   (minutes come from the MDP policy)

The tutor is a pure function of (destination, history): it keeps no state, so the same history
always produces the same decision and every number can be reproduced.

All probabilities below are stated assumptions, informed by the literature and not fitted to
data (the course guidelines allow predefined tables). See docs/REPORT.md for the sources.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import hmm, mdp, readiness, search
from .content import CoursePack, Item

STATES = ("unknown", "fragile", "mastered")
ACTIONS = ("explain", "practice", "advance")
OBSERVATIONS = ("correct_sure", "correct_unsure", "wrong_unsure", "wrong_sure")
U, F, M = 0, 1, 2


@dataclass(frozen=True)
class TutorModel:
    """Every tunable number of the tutor, in one place."""

    prior: tuple[float, ...] = (0.50, 0.30, 0.20)

    p_correct: tuple[float, ...] = (0.25, 0.65, 0.92)

    p_sure_given_correct: tuple[float, ...] = (0.15, 0.45, 0.90)
    p_sure_given_wrong: tuple[float, ...] = (0.20, 0.30, 0.60)

    transition_explain: tuple[tuple[float, ...], ...] = ((0.35, 0.65, 0.00), (0.00, 0.85, 0.15), (0.00, 0.00, 1.00))
    transition_practice: tuple[tuple[float, ...], ...] = ((0.90, 0.10, 0.00), (0.00, 0.60, 0.40), (0.00, 0.00, 1.00))

    minutes: tuple[tuple[str, float], ...] = (("explain", 2.0), ("practice", 1.0), ("advance", 0.0))
    reward_advance: tuple[float, ...] = (-15.0, -5.0, 10.0)
    gamma: float = 0.95

    soft_penalty: float = 0.4
    checkpoint_minutes: float = 1.0
    max_steps_per_skill: int = 12
    pass_fraction: float = 0.7

    def minutes_of(self, action: str) -> float:
        return dict(self.minutes)[action]

    def transition(self, action: str) -> hmm.Matrix:
        table = self.transition_explain if action == "explain" else self.transition_practice
        return [list(row) for row in table]

    def emission(self) -> hmm.Matrix:
        """B[state][observation] = P(observation | state) over the four observation symbols."""
        rows = []
        for s in range(len(STATES)):
            c, sc, sw = self.p_correct[s], self.p_sure_given_correct[s], self.p_sure_given_wrong[s]
            rows.append([c * sc, c * (1 - sc), (1 - c) * (1 - sw), (1 - c) * sw])
        return rows

    def likelihood(self, observation: str) -> hmm.Vector:
        column = OBSERVATIONS.index(observation)
        return [row[column] for row in self.emission()]

    def build_mdp(self) -> mdp.MDP:
        return mdp.MDP(
            states=STATES,
            actions=ACTIONS,
            transitions={"explain": self.transition("explain"), "practice": self.transition("practice")},
            rewards={
                "explain": [-self.minutes_of("explain")] * 3,
                "practice": [-self.minutes_of("practice")] * 3,
                "advance": list(self.reward_advance),
            },
            terminal_actions=frozenset({"advance"}),
            gamma=self.gamma,
        )


@dataclass(frozen=True)
class Event:
    """One thing that happened: a lesson read, a question answered, or a skill left behind."""

    skill: str
    action: str
    item: str | None = None
    choice: int | None = None
    sure: bool | None = None
    auto: bool = False
    capped: bool = False

    def to_json(self) -> dict:
        data: dict = {"skill": self.skill, "action": self.action}
        if self.action == "practice":
            data.update(item=self.item, choice=self.choice, sure=self.sure)
        if self.auto:
            data["auto"] = True
        if self.capped:
            data["capped"] = True
        return data


def observation_of(correct: bool, sure: bool) -> str:
    if correct:
        return "correct_sure" if sure else "correct_unsure"
    return "wrong_sure" if sure else "wrong_unsure"


@dataclass
class Tutor:
    pack: CoursePack
    model: TutorModel = field(default_factory=TutorModel)

    def __post_init__(self) -> None:
        self.mdp = self.model.build_mdp()
        self.solution = mdp.value_iteration(self.mdp)
        self.minutes_to_master = mdp.expected_cost_to_finish(self.mdp, self.solution.policy, dict(self.model.minutes))
        self.hard = {sid: s.hard for sid, s in self.pack.skills.items()}
        self.soft = {sid: s.soft for sid, s in self.pack.skills.items()}
        self._advance_threshold = self._find_advance_threshold()


    def steps_for(self, events: list[Event]) -> list[hmm.Step]:
        """Translate the events of one skill into HMM steps (advance carries no information)."""
        steps = []
        for event in events:
            if event.action == "explain":
                steps.append(hmm.Step(self.model.transition("explain")))
            elif event.action == "practice":
                item = self.pack.items[event.item]
                observation = observation_of(event.choice == item.answer, bool(event.sure))
                steps.append(hmm.Step(self.model.transition("practice"), self.model.likelihood(observation)))
        return steps

    def belief(self, events: list[Event]) -> hmm.Vector:
        return hmm.filtered_belief(list(self.model.prior), self.steps_for(events))

    def p_correct(self, belief: hmm.Vector) -> float:
        """Predicted probability that the next answer on this skill is correct."""
        return sum(belief[s] * self.model.p_correct[s] for s in range(len(STATES)))


    def action_values(self, belief: hmm.Vector) -> dict[str, float]:
        return mdp.qmdp_values(self.solution.q, belief)

    def lookahead_values(self, belief: hmm.Vector, depth: int = 1) -> dict[str, float]:
        """Expectimax over the belief: imagine each possible answer, then act best afterwards.

        QMDP never values information. This closes that gap for `depth` steps: a chance node
        averages over the four possible observations, a max node picks the best follow-up, and
        QMDP scores the leaves. Used as an ablation in the experiments (see simulate.py); the
        product keeps plain QMDP because it is explainable in one line.
        """
        if depth <= 0:
            return self.action_values(belief)
        gamma, states = self.model.gamma, range(len(STATES))
        after_lesson = hmm.predict(belief, self.model.transition("explain"))
        total = 0.0
        for observation in OBSERVATIONS:
            likelihood = self.model.likelihood(observation)
            probability = sum(likelihood[s] * belief[s] for s in states)
            if probability > 0.0:
                posterior = [likelihood[s] * belief[s] / probability for s in states]
                after = hmm.predict(posterior, self.model.transition("practice"))
                total += probability * max(self.lookahead_values(after, depth - 1).values())
        return {
            "explain": -self.model.minutes_of("explain") + gamma * max(self.lookahead_values(after_lesson, depth - 1).values()),
            "practice": -self.model.minutes_of("practice") + gamma * total,
            "advance": sum(belief[s] * self.model.reward_advance[s] for s in states),
        }

    def expected_minutes(self, skill: str, belief: hmm.Vector) -> float:
        """Base A* step cost: expected minutes to master the skill from the current belief."""
        expected = sum(belief[s] * self.minutes_to_master[s] for s in range(len(STATES)))
        return self.pack.skills[skill].effort * (expected + self.model.checkpoint_minutes)

    def advance_threshold(self) -> float:
        """Smallest P(mastered) at which advancing beats practising, when P(unknown) = 0."""
        return self._advance_threshold

    def _find_advance_threshold(self) -> float:
        for thousandth in range(1001):
            m = thousandth / 1000
            values = self.action_values([0.0, 1.0 - m, m])
            if values["advance"] >= max(values["practice"], values["explain"]):
                return m
        return 1.0


    def route_problem(self, completed: frozenset[str], targets: frozenset[str], beliefs: dict[str, hmm.Vector]) -> search.RouteProblem:
        base_cost = {sid: self.expected_minutes(sid, beliefs[sid]) for sid in self.pack.skills}
        return search.RouteProblem(self.hard, self.soft, base_cost, completed, targets, self.model.soft_penalty)


    def clean(self, history: list) -> tuple[list[Event], int]:
        """Keep only well-formed events; malformed input is ignored, never fatal.

        Nothing is dropped for being old: an early "advance" matters as much as a late one.
        The HTTP layer bounds the size of a request instead.
        """
        events, ignored = [], 0
        for raw in history if isinstance(history, list) else []:
            event = self._parse(raw)
            if event is None:
                ignored += 1
            else:
                events.append(event)
        return events, ignored

    def _parse(self, raw: object) -> Event | None:
        if not isinstance(raw, dict):
            return None
        skill, action = raw.get("skill"), raw.get("action")
        if not isinstance(skill, str) or not isinstance(action, str):
            return None
        if skill not in self.pack.skills or action not in ACTIONS:
            return None
        if action == "advance":
            return Event(skill, action, auto=bool(raw.get("auto")), capped=bool(raw.get("capped")))
        if action == "explain":
            return Event(skill, action)
        item = self.pack.items.get(raw.get("item")) if isinstance(raw.get("item"), str) else None
        choice, sure = raw.get("choice"), raw.get("sure")
        if item is None or item.skill != skill or isinstance(choice, bool) or not isinstance(choice, int):
            return None
        if not 0 <= choice < len(item.options) or not isinstance(sure, bool):
            return None
        return Event(skill, action, item.id, choice, sure)

    def pick_item(self, skill: str, events: list[Event], belief: hmm.Vector) -> Item:
        """Choose the next question: unseen first, difficulty matched to the belief.

        Level 1 while the skill is probably unknown, level 3 once it is probably mastered.
        When every question was seen, repeat one whose latest attempt was wrong (the most recent
        such), otherwise the one seen longest ago; never the same question twice in a row.
        """
        items = self.pack.items_by_skill[skill]
        seen = [e for e in events if e.action == "practice"]
        seen_ids = {e.item for e in seen}
        unseen = [i for i in items if i.id not in seen_ids]
        target_level = 1 if belief[M] < 0.3 else 2 if belief[M] < 0.7 else 3
        if unseen:
            return min(unseen, key=lambda i: (abs(i.level - target_level), i.level, i.id))
        last_seen = {e.item: n for n, e in enumerate(seen)}
        still_wrong = {e.item: e.choice != self.pack.items[e.item].answer for e in seen}
        previous = seen[-1].item if len(items) > 1 else None
        candidates = [i for i in items if i.id != previous]
        wrong = [i for i in candidates if still_wrong[i.id]]
        if wrong:
            return max(wrong, key=lambda i: last_seen[i.id])
        return min(candidates, key=lambda i: last_seen[i.id])

    def replay(self, targets: list[str], history: list, pin: str | None = None,
               lesson: bool = False, inspect: str | None = None) -> dict:
        """Compute the full state of a session from its destination and history.

        pin      a skill the learner chose to study now, overriding the route
        lesson   the learner asked for the lesson instead of the recommended step
        inspect  the skill whose HMM trace to return (defaults to the current skill, or to the
                 last skill studied while the current one has no steps yet)
        """
        skills = self.pack.skills
        target_set = self._targets(targets)
        events, ignored = self.clean(history)
        appended: list[Event] = []
        if not isinstance(pin, str) or pin not in skills:
            pin = None
        if not isinstance(inspect, str) or inspect not in skills:
            inspect = None

        while True:
            by_skill: dict[str, list[Event]] = {sid: [] for sid in skills}
            for event in events:
                by_skill[event.skill].append(event)
            completed = frozenset(e.skill for e in events if e.action == "advance")
            beliefs = {sid: self.belief(by_skill[sid]) for sid in skills}
            problem = self.route_problem(completed, target_set, beliefs)
            plan = search.plan_route(problem)
            order, detour = self._choose_order(problem, plan, events, completed, pin)
            reviewing = pin is not None and pin in completed
            current = pin if reviewing else (order[0] if order else None)
            if current is None:
                break
            values = self.action_values(beliefs[current])
            action = mdp.greedy_action(values)
            done_steps = sum(1 for e in by_skill[current] if e.action != "advance")
            capped = done_steps >= self.model.max_steps_per_skill
            if reviewing:
                action = "explain" if lesson else "practice"
                break
            if lesson and not capped:
                action = "explain"
                break
            if action == "advance" or capped:
                auto = Event(current, "advance", auto=True, capped=capped and action != "advance")
                events.append(auto)
                appended.append(auto)
                if current == pin:
                    pin = None
                lesson = False
                continue
            break

        route = self._describe_route(problem, order)
        studied = [e.skill for e in events if e.action != "advance"]
        if inspect:
            focus = inspect
        elif current is not None and any(e.action != "advance" for e in by_skill[current]):
            focus = current
        else:
            focus = studied[-1] if studied else current
        state = {
            "pack": {"id": self.pack.id, "title": self.pack.title},
            "targets": sorted(target_set),
            "append": [e.to_json() for e in appended],
            "ignored_events": ignored,
            "done": current is None,
            "skills": self._describe_skills(beliefs, by_skill, completed, problem, order, current),
            "route": {
                "stops": route,
                "eta_minutes": sum(stop["minutes"] for stop in route),
                "optimal_minutes": plan.cost if plan.found else 0.0,
                "detour_minutes": detour,
                "search": {
                    "expanded": plan.expanded, "generated": plan.generated, "max_frontier": plan.max_frontier,
                    "required": sorted(problem.required), "optional": sorted(problem.relevant - problem.required),
                    "log": [
                        {"state": sorted(entry["state"] - completed), "g": entry["g"], "h": entry["h"], "f": entry["f"]}
                        for entry in plan.log
                    ],
                },
            },
            "current": None,
            "last": self._describe_last(events, by_skill),
            "readiness": self._describe_readiness(target_set, beliefs),
            "calibration": self._describe_calibration(events),
            "elapsed_minutes": sum(self.model.minutes_of(e.action) for e in events),
            "answered": sum(1 for e in events if e.action == "practice"),
            "trace": self.trace(focus, by_skill[focus]) if focus else None,
        }
        if current is not None:
            state["current"] = self._describe_current(current, action, values, beliefs[current], by_skill[current], reviewing, lesson)
        return state

    def _targets(self, targets: object) -> frozenset[str]:
        """The valid target skills, or the first destination when none is valid."""
        chosen = frozenset(t for t in targets if isinstance(t, str) and t in self.pack.skills) if isinstance(targets, (list, tuple)) else frozenset()
        return chosen or frozenset(self.pack.destinations[0]["targets"])

    def _choose_order(self, problem: search.RouteProblem, plan: search.SearchResult, events: list[Event],
                      completed: frozenset[str], pin: str | None) -> tuple[list[str], float]:
        """Decide the order of skills to show. Returns (order, detour minutes vs the optimum).

        A* gives the optimal order. Two things may change the first stop:
        * a pinned skill: the learner's choice wins, and the cost of the detour is reported;
        * the skill in progress: stay on it when that is still optimal, so that ties between
          equally good routes never make the tutor jump between topics.
        """
        order = list(plan.actions)
        def available(skill: str | None) -> bool:
            return skill is not None and skill not in completed and self.hard[skill] <= completed

        last = next((e.skill for e in reversed(events) if e.action != "advance"), None)
        focus = pin if available(pin) else last
        if not available(focus):
            return self._coherent(problem, order, keep_first=False), 0.0
        if order and order[0] == focus:
            return self._coherent(problem, order, keep_first=True), 0.0
        first_cost = problem.step_cost(focus, problem.initial)
        rest_problem = search.RouteProblem(self.hard, self.soft, problem.base_cost, completed | {focus},
                                           problem.targets, self.model.soft_penalty)
        rest = search.plan_route(rest_problem, log_limit=0)
        detour = first_cost + rest.cost - plan.cost
        if detour < 1e-9:
            detour = 0.0
        if focus == pin or detour == 0.0:
            return self._coherent(problem, [focus] + rest.actions, keep_first=True), detour
        return self._coherent(problem, order, keep_first=False), 0.0

    def _coherent(self, problem: search.RouteProblem, order: list[str], keep_first: bool) -> list[str]:
        """Among routes of equal cost, show the one that switches topic least.

        A* fixes which skills are studied and what the route costs. Many orders share that cost,
        so the order shown follows each prerequisite thread to its end (then the course's week
        order) instead of jumping between topics. The cost is re-checked; if it differs, the
        original A* order is kept.
        """
        if len(order) < 3:
            return order
        position = {skill: n for n, skill in enumerate(order)}
        parents = {s: self.hard[s] | self.soft[s] for s in order}
        before = {s: {p for p in parents[s] if p in position and position[p] < position[s]} for s in order}
        skills = self.pack.skills
        result = [order[0]] if keep_first else []
        remaining = [s for s in order if s not in result]
        while remaining:
            done, last = set(result), (result[-1] if result else None)

            def rank(skill: str) -> tuple:
                follows = last is not None and last in parents[skill]
                same_topic = last is not None and skills[skill].group == skills[last].group
                return (not follows, not same_topic, skills[skill].week, position[skill])

            chosen = min((s for s in remaining if before[s] <= done), key=rank)
            result.append(chosen)
            remaining.remove(chosen)
        same_cost = abs(problem.route_cost(result) - problem.route_cost(order)) < 1e-9
        return result if same_cost else order

    def _describe_route(self, problem: search.RouteProblem, order: list[str]) -> list[dict]:
        stops, state = [], problem.initial
        for skill in order:
            missing = sorted(p for p in self.soft[skill] if p not in state)
            stops.append({"skill": skill, "minutes": problem.step_cost(skill, state),
                          "base_minutes": problem.base_cost[skill], "missing_soft": missing})
            state = state | {skill}
        return stops

    def _describe_skills(self, beliefs, by_skill, completed, problem, order, current) -> list[dict]:
        described = []
        for sid, skill in self.pack.skills.items():
            if sid in completed:
                status = "completed"
            elif sid == current:
                status = "current"
            elif sid in order:
                status = "route"
            elif sid in problem.relevant:
                status = "optional"
            else:
                status = "off"
            described.append({
                "id": sid, "name": skill.name, "short": skill.short, "group": skill.group, "week": skill.week,
                "hard": sorted(skill.hard), "soft": sorted(skill.soft), "x": skill.x, "y": skill.y,
                "belief": beliefs[sid], "p_correct": self.p_correct(beliefs[sid]),
                "status": status, "locked": not skill.hard <= completed and sid not in completed,
                "steps": sum(1 for e in by_skill[sid] if e.action != "advance"),
                "minutes": problem.base_cost[sid],
            })
        return described

    def _describe_current(self, skill: str, action: str, values: dict[str, float], belief: hmm.Vector,
                          events: list[Event], reviewing: bool, lesson: bool) -> dict:
        recommended = mdp.greedy_action(values)
        current = {
            "skill": skill, "action": action, "recommended": recommended, "values": values,
            "belief": belief, "p_correct": self.p_correct(belief),
            "steps": sum(1 for e in events if e.action != "advance"),
            "reviewing": reviewing, "overridden": action != recommended,
            "reason": self._reason(action, recommended, values, belief, reviewing, lesson),
        }
        if action == "practice":
            item = self.pick_item(skill, events, belief)
            current["item"] = {"id": item.id, "level": item.level, "prompt": item.prompt, "options": list(item.options)}
        else:
            current["lesson"] = self.pack.lessons[skill]
        return current

    def _reason(self, action, recommended, values, belief, reviewing, lesson) -> str:
        if reviewing:
            return "You chose to review a completed skill. Every answer still updates the estimate."
        if action == "explain" and recommended != "explain" and lesson:
            return (f"You asked for the lesson. The tutor would have picked {recommended} "
                    f"({values[recommended]:.2f} vs {values['explain']:.2f}), and your choice wins.")
        if action == "explain":
            return (f"P(unknown) is {belief[U]:.2f}. Testing something you have not learnt mostly measures guessing, "
                    f"so a short lesson has the highest expected value ({values['explain']:.2f} vs {values['practice']:.2f}).")
        return (f"P(mastered) is {belief[M]:.2f}. A question both strengthens memory and measures it, "
                f"so practice has the highest expected value ({values['practice']:.2f} vs {values['explain']:.2f} for a lesson, "
                f"{values['advance']:.2f} for moving on).")

    def _describe_last(self, events: list[Event], by_skill: dict[str, list[Event]]) -> dict | None:
        """Feedback for the most recent lesson or answer (an advance carries nothing to explain)."""
        index = next((n for n in range(len(events) - 1, -1, -1) if events[n].action != "advance"), None)
        if index is None:
            return None
        event = events[index]
        position = sum(1 for e in events[: index + 1] if e.skill == event.skill and e.action != "advance")
        skill_events = [e for e in by_skill[event.skill] if e.action != "advance"][:position]
        trace = hmm.forward(list(self.model.prior), self.steps_for(skill_events))
        if not trace:
            return None
        last = {
            "skill": event.skill, "action": event.action,
            "belief_before": trace[-1].prior, "belief_after": trace[-1].predicted,
            "advanced": [e.to_json() for e in events[index + 1:] if e.action == "advance"],
        }
        if event.action == "practice":
            item = self.pack.items[event.item]
            last.update({
                "item": item.id, "prompt": item.prompt, "options": list(item.options), "choice": event.choice,
                "answer": item.answer, "correct": event.choice == item.answer, "sure": event.sure, "why": item.why,
                "posterior": trace[-1].posterior, "evidence_probability": trace[-1].evidence_probability,
            })
        return last

    def _describe_readiness(self, targets: frozenset[str], beliefs: dict[str, hmm.Vector]) -> dict:
        scope = sorted(self.pack.hard_closure(targets))
        probabilities = [self.p_correct(beliefs[sid]) for sid in scope]
        return {
            "skills": scope,
            "expected_score": sum(probabilities) / len(probabilities),
            "pass_probability": readiness.pass_probability(probabilities, self.model.pass_fraction),
            "pass_fraction": self.model.pass_fraction,
            "mastered": sum(1 for sid in scope if beliefs[sid][M] >= self.advance_threshold()),
        }

    def _describe_calibration(self, events: list[Event]) -> dict:
        """How well the learner's confidence and the model's forecasts match reality so far."""
        sure = {"n": 0, "correct": 0}
        unsure = {"n": 0, "correct": 0}
        forecasts: list[tuple[float, bool]] = []
        ledger: list[dict] = []
        beliefs: dict[str, hmm.Vector] = {}
        for event in events:
            belief = beliefs.get(event.skill, list(self.model.prior))
            if event.action == "practice":
                correct = event.choice == self.pack.items[event.item].answer
                bucket = sure if event.sure else unsure
                bucket["n"] += 1
                bucket["correct"] += int(correct)
                forecast = self.p_correct(belief)
                forecasts.append((forecast, correct))
                ledger.append({"skill": event.skill, "item": event.item, "forecast": forecast, "correct": correct})
                belief, _ = hmm.condition(belief, self.model.likelihood(observation_of(correct, bool(event.sure))))
                belief = hmm.predict(belief, self.model.transition("practice"))
            elif event.action == "explain":
                belief = hmm.predict(belief, self.model.transition("explain"))
            beliefs[event.skill] = belief
        count = len(forecasts)
        return {
            "sure": sure, "unsure": unsure, "forecasts": count,
            "brier": sum((p - int(c)) ** 2 for p, c in forecasts) / count if count else None,
            "mean_forecast": sum(p for p, _ in forecasts) / count if count else None,
            "observed": sum(int(c) for _, c in forecasts) / count if count else None,
            "ledger": ledger[-40:],
        }

    def trace(self, skill: str, events: list[Event]) -> dict:
        """Every number of the HMM for one skill: forward steps and the Viterbi path."""
        real = [e for e in events if e.action != "advance"]
        steps = self.steps_for(real)
        prior = list(self.model.prior)
        forward = hmm.forward(prior, steps)
        path, log_probability = hmm.viterbi(prior, steps)
        rows = []
        for n, (event, step, result) in enumerate(zip(real, steps, forward)):
            row = {
                "n": n + 1, "action": event.action, "prior": result.prior, "posterior": result.posterior,
                "predicted": result.predicted, "likelihood": step.likelihood,
                "evidence_probability": result.evidence_probability, "viterbi": STATES[path[n]],
            }
            if event.action == "practice":
                item = self.pack.items[event.item]
                row["observation"] = observation_of(event.choice == item.answer, bool(event.sure))
                row["item"] = item.id
            rows.append(row)
        return {
            "skill": skill, "prior": prior, "steps": rows,
            "belief": forward[-1].predicted if forward else prior,
            "viterbi": [STATES[s] for s in path], "viterbi_log_probability": log_probability,
        }

    def describe_model(self) -> dict:
        """The fixed part of the engine: parameters, the solved MDP and its convergence."""
        solution = self.solution
        shown = [0, 1, 2, 3, 4, 9, 19, 49, 99, 199]
        return {
            "states": list(STATES), "actions": list(ACTIONS), "observations": list(OBSERVATIONS),
            "prior": list(self.model.prior), "emission": self.model.emission(),
            "p_correct": list(self.model.p_correct),
            "transitions": {a: self.model.transition(a) for a in ("explain", "practice")},
            "rewards": {a: self.mdp.rewards[a] for a in ACTIONS}, "gamma": self.model.gamma,
            "values": solution.values, "q": solution.q, "policy": solution.policy,
            "iterations": solution.iterations,
            "history": [
                {"sweep": k + 1, "values": solution.history[k][0], "residual": solution.history[k][1]}
                for k in sorted(set(shown + [solution.iterations - 1])) if k < solution.iterations
            ],
            "minutes_to_master": self.minutes_to_master, "advance_threshold": self.advance_threshold(),
            "soft_penalty": self.model.soft_penalty, "checkpoint_minutes": self.model.checkpoint_minutes,
            "max_steps_per_skill": self.model.max_steps_per_skill, "pass_fraction": self.model.pass_fraction,
            "minutes": dict(self.model.minutes),
        }

    def compare_search(self, targets: list[str], history: list) -> list[dict]:
        """Run A*, UCS, greedy and BFS on the same route problem (for the engine room)."""
        events, _ = self.clean(history)
        completed = frozenset(e.skill for e in events if e.action == "advance")
        by_skill: dict[str, list[Event]] = {sid: [] for sid in self.pack.skills}
        for event in events:
            by_skill[event.skill].append(event)
        beliefs = {sid: self.belief(by_skill[sid]) for sid in self.pack.skills}
        problem = self.route_problem(completed, self._targets(targets), beliefs)
        results = [
            search.astar(problem, problem.heuristic, log_limit=0),
            search.uniform_cost_search(problem),
            search.greedy_best_first(problem, problem.heuristic),
            search.breadth_first_search(problem),
        ]
        optimum = results[1].cost
        return [
            {"algorithm": r.algorithm, "cost": r.cost if r.found else None, "expanded": r.expanded, "generated": r.generated,
             "max_frontier": r.max_frontier, "stops": len(r.actions), "optimal": abs(r.cost - optimum) < 1e-9,
             "route": r.actions}
            for r in results
        ]

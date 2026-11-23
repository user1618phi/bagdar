"""Command line entry point.

    python -m bagdar                 start the web app (same as `serve`)
    python -m bagdar serve           start the web app on http://127.0.0.1:8000
    python -m bagdar demo            console walk-through: input -> key steps -> output per algorithm
    python -m bagdar experiments     run the simulation experiments and write docs/results.json
    python -m bagdar realdata        fit and test the knowledge model on real answer logs (ASSISTments)
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from . import hmm, mdp, search
from .content import load_pack
from .tutor import ACTIONS, OBSERVATIONS, STATES, Tutor


def _vector(values, digits: int = 3) -> str:
    return "[" + ", ".join(f"{v:.{digits}f}" for v in values) + "]"


def demo() -> None:
    """Print one small worked example per algorithm, then show them working together."""
    tutor = Tutor(load_pack())
    model = tutor.model
    line = "-" * 78

    print(line)
    print("1. HIDDEN MARKOV MODEL  -  where is the learner?")
    print(line)
    print(f"States {STATES}; prior {_vector(model.prior, 2)}")
    print("Emission table P(observation | state):")
    print(f"  {'':<10}" + "".join(f"{o:>16}" for o in OBSERVATIONS))
    for state, row in zip(STATES, model.emission()):
        print(f"  {state:<10}" + "".join(f"{p:>16.4f}" for p in row))
    observations = ["wrong_unsure", "correct_unsure", "correct_sure"]
    print(f"Input: three answers on one skill: {observations}")
    steps = [hmm.Step(model.transition("practice"), model.likelihood(o)) for o in observations]
    for n, (observation, result) in enumerate(zip(observations, hmm.forward(list(model.prior), steps)), 1):
        print(f"  answer {n}: {observation}")
        print(f"    prior      {_vector(result.prior)}")
        print(f"    likelihood {_vector(model.likelihood(observation), 4)}   P(evidence) = {result.evidence_probability:.4f}")
        print(f"    posterior  {_vector(result.posterior)}   (Bayes' rule: likelihood x prior, normalised)")
        print(f"    predicted  {_vector(result.predicted)}   (after the learning transition)")
    path, log_probability = hmm.viterbi(list(model.prior), steps)
    print(f"Output: belief {_vector(hmm.filtered_belief(list(model.prior), steps))}")
    print(f"        Viterbi path {[STATES[s] for s in path]} (log probability {log_probability:.3f})")
    print("Why: answers are noisy (guesses and slips), so knowledge is tracked as a probability, not a score.")

    print()
    print(line)
    print("2. MARKOV DECISION PROCESS  -  what should happen next?")
    print(line)
    print(f"Actions {ACTIONS}; discount gamma = {model.gamma}; rewards are minutes (time costs, mastery pays)")
    print("Input: transition tables P(next | state, action) and rewards R(state, action)")
    for action in ("explain", "practice"):
        print(f"  {action:<9} R = {-model.minutes_of(action):>5.1f}   T = {[list(r) for r in model.transition(action)]}")
    print(f"  advance   R = {list(model.reward_advance)} (ends the episode)")
    solution = tutor.solution
    print("Value iteration, Bellman update V(s) <- max_a [ R(s,a) + gamma * sum_s' P(s'|s,a) V(s') ]:")
    for sweep in (0, 1, 2, 9, solution.iterations - 1):
        values, residual = solution.history[sweep]
        print(f"  sweep {sweep + 1:>3}: V = {_vector(values)}   largest change = {residual:.2e}")
    print("Q*(state, action):")
    print(f"  {'':<10}" + "".join(f"{a:>10}" for a in ACTIONS))
    for index, state in enumerate(STATES):
        print(f"  {state:<10}" + "".join(f"{solution.q[a][index]:>10.3f}" for a in ACTIONS))
    print(f"Output: policy {dict(zip(STATES, solution.policy))}")
    belief = hmm.filtered_belief(list(model.prior), steps)
    values = tutor.action_values(belief)
    print(f"        on the belief above, Q(b, a) = {{{', '.join(f'{a}: {v:.2f}' for a, v in values.items())}}} -> {mdp.greedy_action(values)}")
    print(f"        advancing starts to win at P(mastered) >= {tutor.advance_threshold():.3f}")
    print("Why: moving on too early and practising too long both cost time; the MDP weighs them exactly.")

    print()
    print(line)
    print("3. A* SEARCH  -  which skill comes next?")
    print(line)
    targets = frozenset(tutor.pack.destinations[0]["targets"])
    beliefs = {sid: list(model.prior) for sid in tutor.pack.skills}
    problem = tutor.route_problem(frozenset(), targets, beliefs)
    print(f"Input: destination {sorted(targets)}; state = set of completed skills; start = nothing completed")
    print("       step cost = expected minutes from the belief (HMM) and the policy (MDP), +40% per missing soft prerequisite")
    print("       h(state) = sum of base minutes of the required skills still missing (admissible, consistent)")
    result = search.plan_route(problem)
    for entry in result.log[:6]:
        print(f"  expand {{{', '.join(sorted(entry['state'])) or 'start'}}}:  g = {entry['g']:.2f}  h = {entry['h']:.2f}  f = {entry['f']:.2f}")
    print(f"  ... {result.expanded} states expanded in total")
    shown = tutor._coherent(problem, result.actions, keep_first=False)
    print(f"Output: route {' -> '.join(shown)}")
    print(f"        cost {result.cost:.1f} minutes (A* found: {' -> '.join(result.actions)};")
    print("        many orders tie on cost, so the one shown follows each topic to its end)")
    for other in (search.uniform_cost_search(problem), search.greedy_best_first(problem, problem.heuristic), search.breadth_first_search(problem)):
        print(f"        {other.algorithm:<7} cost {other.cost:6.1f}  expanded {other.expanded:>5}")
    print(f"        {'A*':<7} cost {result.cost:6.1f}  expanded {result.expanded:>5}")
    print("Why: soft prerequisites make some orders cheaper than others; A* finds the cheapest without trying them all.")

    print()
    print(line)
    print("4. TOGETHER  -  one session, three algorithms")
    print(line)
    history: list[dict] = []
    answers = iter([(False, False), (True, False), (True, True), (True, True), (True, True), (True, True)])
    for _ in range(8):
        state = tutor.replay(sorted(targets), history)
        history += state["append"]
        for auto in state["append"]:
            print(f"  [MDP] advance: {auto['skill']} is completed")
        current = state["current"]
        if current is None:
            break
        stops = " -> ".join(stop["skill"] for stop in state["route"]["stops"][:4])
        print(f"  [A*]  route: {stops} ...  ETA {state['route']['eta_minutes']:.0f} min, pass chance {state['readiness']['pass_probability']:.0%}")
        print(f"  [HMM] {current['skill']}: belief {_vector(current['belief'], 2)}")
        print(f"  [MDP] Q = {{{', '.join(f'{a}: {v:.2f}' for a, v in current['values'].items())}}} -> {current['action']}")
        if current["action"] == "explain":
            history.append({"skill": current["skill"], "action": "explain"})
            print("        learner reads the lesson")
        else:
            correct, sure = next(answers, (True, True))
            item = tutor.pack.items[current["item"]["id"]]
            choice = item.answer if correct else (item.answer + 1) % len(item.options)
            history.append({"skill": current["skill"], "action": "practice", "item": item.id, "choice": choice, "sure": sure})
            print(f"        learner answers {item.id}: {'correct' if correct else 'wrong'}, {'sure' if sure else 'not sure'}")
    print("Why: each algorithm feeds the next. The belief sets the action and the route cost; the route sets the skill.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="bagdar", description="Bagdar: a GPS for learning.")
    commands = parser.add_subparsers(dest="command")
    serve = commands.add_parser("serve", help="start the web app")
    serve.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    serve.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    serve.add_argument("--no-browser", action="store_true", help="do not open the browser")
    serve.add_argument("--verbose", action="store_true", help="log every request")
    commands.add_parser("demo", help="console walk-through of the three algorithms")
    experiments = commands.add_parser("experiments", help="run the simulation experiments")
    experiments.add_argument("--episodes", type=int, default=20_000)
    experiments.add_argument("--profiles", type=int, default=200)
    experiments.add_argument("--seed", type=int, default=7)
    real = commands.add_parser("realdata", help="fit and test the knowledge model on real answer logs")
    real.add_argument("--csv", type=Path, default=None, help="path to skill_builder_data_corrected.csv (downloaded if missing)")
    real.add_argument("--iterations", type=int, default=30)
    args = parser.parse_args()

    if args.command == "demo":
        demo()
    elif args.command == "experiments":
        from .simulate import print_summary, write_results

        target = Path(__file__).resolve().parent.parent / "docs" / "results.json"
        print_summary(write_results(target, episodes=args.episodes, profiles=args.profiles, seed=args.seed))
        print(f"\nSaved to {target}")
    elif args.command == "realdata":
        from . import realdata

        target = Path(__file__).resolve().parent.parent / "docs" / "results_real.json"
        results = realdata.run(args.csv or realdata.DEFAULT_CSV, args.iterations)
        target.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        realdata.print_summary(results)
        print(f"\nSaved to {target}")
    else:
        from .server import serve as run

        run(getattr(args, "host", os.environ.get("HOST", "127.0.0.1")), getattr(args, "port", int(os.environ.get("PORT", "8000"))),
            not getattr(args, "no_browser", False), getattr(args, "verbose", False))


if __name__ == "__main__":
    main()

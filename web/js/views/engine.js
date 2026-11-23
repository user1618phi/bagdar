// Engine: every number behind the decisions. One tab per algorithm, plus the evidence.

import { h, fmt, table, STATE_NAMES, OBSERVATION_LABEL, ACTION_LABEL } from "../ui.js";

const TABS = [["hmm", "hmm"], ["mdp", "mdp"], ["astar", "a*"], ["evidence", "evidence"]];

export function renderEngine(app, actions) {
  const { ui } = app;
  const index = Math.max(0, TABS.findIndex(([id]) => id === ui.engineTab));
  const sheets = { hmm, mdp, astar, evidence };
  return h("div", { class: `engine${ui.fresh ? " enter" : ""}` },
    h("div", { class: "enginehead" },
      h("h2", {}, "Under the hood: ", h("span", { class: "acc", text: "every number" }), " is shown"),
      h("div", { class: "seg", role: "tablist", "aria-label": "Algorithm" },
        h("span", { class: "seg-ind", style: { transform: `translateX(${index * 100}%)` }, "aria-hidden": "true" }),
        TABS.map(([id, label]) => h("button", {
          type: "button", role: "tab", "aria-selected": String(id === TABS[index][0]), text: label,
          onClick: () => actions.set({ engineTab: id }),
        })))),
    h("div", { class: "sheet", role: "tabpanel" }, sheets[TABS[index][0]](app, actions)));
}

// ---------------------------------------------------------------- HMM

function hmm(app, actions) {
  const { state, model } = app;
  const trace = state.trace;
  const options = [...state.skills].sort((a, b) => b.steps - a.steps || a.name.localeCompare(b.name));
  const picker = h("select", { class: "field", "aria-label": "Skill to inspect", onChange: (event) => actions.inspect(event.target.value) },
    options.map((skill) => h("option", { value: skill.id, selected: trace && skill.id === trace.skill, text: `${skill.name} (${skill.steps} steps)` })));

  const rows = (trace?.steps ?? []).map((step) => [
    String(step.n),
    step.action === "practice" ? OBSERVATION_LABEL[step.observation] : "lesson read (no evidence)",
    fmt.vector(step.prior),
    step.likelihood ? fmt.vector(step.likelihood, 3) : "—",
    fmt.vector(step.posterior),
    fmt.vector(step.predicted),
    step.viterbi,
  ]);

  return [
    h("p", { class: "lead", text: "A hidden Markov model tracks each skill. The true state (unknown, fragile, mastered) is hidden; answers are noisy evidence of it." }),
    h("div", { class: "formula", text:
      "condition   b(x)  ←  α · P(e | x) · b(x)                 Bayes' rule, after each answer\n" +
      "predict     b(x') ←  Σx b(x) · P(x' | x, action)          the learner changes by acting" }),
    h("div", { class: "pick" }, h("span", { class: "label", text: "skill" }), picker),
    rows.length
      ? table(`forward algorithm, step by step · vectors are [unknown, fragile, mastered] · prior ${fmt.vector(trace.prior)}`,
          ["#", "evidence", "belief before", "likelihood P(e|x)", "after Bayes", "after learning", "viterbi"], rows, { numeric: [0, 2, 3, 4, 5] })
      : h("p", { class: "note", text: "No steps on this skill yet. Answer a question and its row appears here." }),
    trace ? h("p", { class: "note", text:
      `Current belief ${fmt.vector(trace.belief)}. Most likely path (Viterbi): ${trace.viterbi.join(" → ")}. ` +
      "Filtering answers \"where is the learner now\"; Viterbi answers \"what is the single most likely story of how they got here\"." }) : null,
    table("emission table · P(observation | state)", ["state", ...model.observations.map((o) => OBSERVATION_LABEL[o])],
      model.emission.map((row, s) => [STATE_NAMES[s], ...row.map((p) => fmt.num(p, 4))]), { numeric: [1, 2, 3, 4] }),
    h("p", { class: "note", text: "An unknown skill is answered correctly 25% of the time (a guess among four options); a mastered one still slips 8% of the time. Confidence is a second signal: a sure, correct answer is far stronger evidence than a hesitant one." }),
  ];
}

// ---------------------------------------------------------------- MDP

function mdp(app) {
  const { state, model } = app;
  const actionNames = model.actions;
  const qRows = STATE_NAMES.map((name, s) => [
    name,
    ...actionNames.map((a) => fmt.num(model.q[a][s], 3)),
    h("span", { class: "mark", text: ACTION_LABEL[model.policy[s]] }),
  ]);
  const sweeps = model.history.map((row) => [String(row.sweep), ...row.values.map((v) => fmt.num(v, 3)), row.residual.toExponential(2)]);
  const parts = [
    h("p", { class: "lead", text: "A Markov decision process decides what to do with one skill. Time is the cost; advancing pays off only when the skill is really mastered." }),
    h("div", { class: "formula", text:
      "Q(s, a)  =  R(s, a) + γ · Σs' P(s' | s, a) · V(s')        γ = " + model.gamma + "\n" +
      "V(s)     =  max a Q(s, a)                                  Bellman optimality equation\n" +
      "Q(b, a)  =  Σs b(s) · Q(s, a)                              acting on a belief (QMDP)" }),
    table("optimal action values Q*(state, action), in minutes", ["true state", ...actionNames.map((a) => ACTION_LABEL[a]), "policy"], qRows, { numeric: [1, 2, 3] }),
    table(`value iteration · converged in ${model.iterations} sweeps`, ["sweep", "V(unknown)", "V(fragile)", "V(mastered)", "largest change"], sweeps, { numeric: [0, 1, 2, 3, 4] }),
    table("the model · P(next state | state, action) and rewards",
      ["action", "from unknown", "from fragile", "from mastered", "reward"],
      [
        ...["explain", "practice"].map((a) => [ACTION_LABEL[a], ...model.transitions[a].map((row) => fmt.vector(row)), `${model.rewards[a][0]} min`]),
        [ACTION_LABEL.advance, "ends", "ends", "ends", fmt.vector(model.rewards.advance, 0)],
      ], { numeric: [1, 2, 3, 4] }),
  ];
  if (state.current) {
    const { belief, values, action } = state.current;
    const rows = Object.entries(values).map(([name, value]) => [
      name === action ? h("span", { class: "mark info", text: ACTION_LABEL[name] }) : ACTION_LABEL[name],
      STATE_NAMES.map((_, s) => `${fmt.p(belief[s])}·${fmt.num(model.q[name][s], 2)}`).join(" + "),
      fmt.num(value, 3),
    ]);
    parts.push(table(`decision right now · belief ${fmt.vector(belief)}`, ["action", "Σ b(s) · Q(s, a)", "value"], rows, { numeric: [1, 2] }));
  }
  parts.push(h("p", { class: "note", text:
    `Moving on starts to win once P(mastered) reaches ${fmt.p3(model.advance_threshold)}. That threshold is not picked by hand: it follows from the cost of one more question against the cost of leaving a skill half-learnt. ` +
    "Known limit: QMDP assumes the uncertainty disappears after one step, so it never asks a question only to learn about the learner." }));
  return parts;
}

// ---------------------------------------------------------------- A*

function astar(app, actions) {
  const { state, ui } = app;
  const byId = Object.fromEntries(state.skills.map((skill) => [skill.id, skill]));
  const search = state.route.search;
  const stops = state.route.stops.map((stop, index) => [
    String(index + 1), byId[stop.skill].name, fmt.num(stop.base_minutes, 1),
    stop.missing_soft.length ? `skipped ${stop.missing_soft.map((id) => byId[id].short).join(", ")}` : "—",
    fmt.num(stop.minutes, 1),
  ]);
  const log = search.log.slice(0, 14).map((entry, index) => [
    String(index + 1),
    entry.state.length ? entry.state.map((id) => byId[id].short).join(", ") : "start",
    fmt.num(entry.g, 1), fmt.num(entry.h, 1), fmt.num(entry.f, 1),
  ]);
  const parts = [
    h("p", { class: "lead", text: "A* search plans the order of skills. A state is the set of skills already completed; a step studies one more; the cost is the expected minutes it takes you." }),
    h("div", { class: "formula", text:
      "f(n) = g(n) + h(n)        g = minutes spent so far,  h = minutes of required skills still missing\n" +
      "cost(skill) = effort · (b · minutes-to-master + 1) · (1 + 0.4 · missing soft prerequisites)" }),
    stops.length
      ? table(`your route · ${fmt.num(state.route.eta_minutes, 1)} minutes`, ["#", "skill", "base min", "soft prerequisites", "minutes"], stops, { numeric: [0, 2, 4] })
      : h("p", { class: "note", text: "You have arrived: nothing left to plan." }),
    log.length ? table(`first expansions · ${search.expanded} states expanded, ${search.generated} generated`,
      ["#", "skills completed in this state", "g", "h", "f"], log, { numeric: [0, 2, 3, 4] }) : null,
    h("p", { class: "note", text:
      "The heuristic never overestimates (every required skill must still be studied, and never faster than its base time), so the first route A* completes is the cheapest. " +
      "Many orders tie on cost; among them the app shows the one that follows each topic to its end." }),
    h("div", { class: "pick" },
      h("button", { class: "btn", type: "button", text: "Compare with UCS, greedy and BFS", onClick: actions.compare }),
      h("span", { class: "label", text: "same problem, four algorithms" })),
  ];
  if (ui.compare?.error) parts.push(h("p", { class: "note", text: ui.compare.error }));
  else if (ui.compare) {
    parts.push(table("search algorithms on your current route problem",
      ["algorithm", "route cost, min", "states expanded", "stops", "result"],
      ui.compare.map((r) => [r.algorithm, r.cost === null ? "—" : fmt.num(r.cost, 1), String(r.expanded), String(r.stops),
        h("span", { class: `mark ${r.optimal ? "ok" : "warn"}`, text: r.optimal ? "optimal" : "not optimal" })]),
      { numeric: [1, 2, 3] }));
  }
  return parts;
}

// ---------------------------------------------------------------- evidence

function evidence(app, actions) {
  const data = app.evidence;
  if (!data) {
    actions.loadEvidence();
    return [h("p", { class: "label", text: "loading the experiment results" })];
  }
  if (data.error) return [h("p", { class: "note", text: data.error })];

  const ledger = app.state.calibration;
  const byId = Object.fromEntries(app.state.skills.map((skill) => [skill.id, skill]));
  const ledgerRows = [...ledger.ledger].reverse().slice(0, 12).map((row) => [
    byId[row.skill].short, row.item, fmt.pct(row.forecast),
    h("span", { class: `mark ${row.correct ? "ok" : "bad"}`, text: row.correct ? "correct" : "wrong" }),
  ]);
  const policyTable = (label, rows) => {
    const best = rows.reduce((top, row, i) => (row.policy.startsWith("Oracle") || row.payoff <= rows[top].payoff ? top : i), 0);
    return table(label, ["decision rule", "minutes per skill", "truly mastered", "left unknown", "payoff"],
      rows.map((row) => [row.policy, fmt.num(row.minutes, 2), fmt.pct(row.mastered), fmt.pct(row.left_unknown), fmt.num(row.payoff, 2)]),
      { numeric: [1, 2, 3, 4], best });
  };
  const bins = data.calibration.matched.bins.map((bin) => [
    `${fmt.pct(bin.range[0])}–${fmt.pct(bin.range[1])}`, String(bin.n), fmt.p3(bin.forecast), fmt.p3(bin.observed), fmt.signed(bin.observed - bin.forecast),
  ]);
  const searchRows = data.search.map((row) => {
    const by = Object.fromEntries(row.algorithms.map((a) => [a.algorithm, a]));
    return [row.destination, String(row.required_skills), fmt.num(by["A*"].expanded, 1), fmt.num(by.UCS.expanded, 1), fmt.num(by.BFS.expanded, 1),
      fmt.pct(by["A*"].optimal_share), fmt.pct(by.Greedy.optimal_share), fmt.pct(by.BFS.optimal_share)];
  });
  const matched = data.calibration.matched;
  const mismatched = data.calibration.mismatched;
  const foreign = data.calibration.foreign;

  const real = data.real;
  const realParts = !real ? [] : [
    h("p", { class: "lead", text: `Real students first. The knowledge model was fitted with Baum-Welch on ${real.students.train.toLocaleString("en")} students and asked to forecast ${real.answers.test.toLocaleString("en")} answers of ${real.students.test} students it had never seen.` }),
    table(`${real.dataset.toLowerCase()} · held-out students · every answer forecast before it is read`,
      ["forecaster", "AUC", "Brier", "accuracy", "calibration error"],
      real.models.map((row) => [row.model, fmt.p3(row.auc), fmt.num(row.brier, 4), fmt.pct(row.accuracy), fmt.p3(row.calibration_error)]),
      { numeric: [1, 2, 3, 4], best: real.models.reduce((top, row, i) => (row.brier < real.models[top].brier ? i : top), 0) }),
    table("what the data taught the model · [unknown, fragile, mastered]",
      ["", "assumed before seeing data", "fitted on real answers"],
      [["P(correct | state)", fmt.vector(real.parameters.assumed.p_correct), fmt.vector(real.parameters.fitted.p_correct)],
       ["prior", fmt.vector(real.parameters.assumed.prior), fmt.vector(real.parameters.fitted.prior)],
       ["P(unknown → fragile)", fmt.p(real.parameters.assumed.transition[0][1]), fmt.p(real.parameters.fitted.transition[0][1])],
       ["P(fragile → mastered)", fmt.p(real.parameters.assumed.transition[1][2]), fmt.p(real.parameters.fitted.transition[1][2])]],
      { numeric: [1, 2] }),
    h("p", { class: "note", text: `${real.note} Source: ${real.citation}. The honest reading: the fitted model with a prior per skill is the most accurate and stays calibrated, but a student's own running average ranks answers almost as well. Reproduce with: python -m bagdar realdata` }),
    h("div", { class: "ruler", role: "presentation" }),
  ];

  return [
    ...realParts,
    h("p", { class: "lead", text: "Simulated learners with a known hidden state, so we can check what is impossible to see in real people: was the skill truly mastered when the tutor moved on?" }),
    h("p", { class: "note", text: `${data.note} Seed ${data.seed}; reproduce with: python -m bagdar experiments` }),
    policyTable(`teaching rules · ${data.episodes.toLocaleString("en")} skills each · learners follow the assumed model`, data.policies.matched),
    policyTable("the same rules · learners with different numbers (luckier guesses, slower learning)", data.policies.mismatched),
    policyTable("the same rules · learners built on a different theory (continuous ability, no hidden states)", data.policies.foreign),
    h("p", { class: "note", text: "Payoff is the reward for the true final state minus minutes spent. A rule tested on its own model wins by construction, so the second and third tables matter more. With wrong numbers the tutor keeps the best payoff but moves on too early more often: the parameters must be fitted to real answers before any claim about real students. The lookahead row is an ablation: one step of expectimax over the possible answers, which repairs QMDP's blindness to information." }),
    table(`are the forecasts honest? · ${matched.answers.toLocaleString("en")} answers · forecast P(correct) against what happened`,
      ["forecast bin", "answers", "mean forecast", "observed", "gap"], bins, { numeric: [1, 2, 3, 4] }),
    h("p", { class: "note", text:
      `Brier score ${fmt.num(matched.brier, 4)} against ${fmt.num(matched.brier_base_rate, 4)} for always predicting the average; calibration error ${fmt.p3(matched.expected_calibration_error)}. ` +
      `With wrong numbers the calibration error grows to ${fmt.p3(mismatched.expected_calibration_error)} and the Brier score (${fmt.num(mismatched.brier, 4)}) no longer beats the average (${fmt.num(mismatched.brier_base_rate, 4)}). ` +
      `On the foreign learners the error is ${fmt.p3(foreign.expected_calibration_error)} and the Brier score ${fmt.num(foreign.brier, 4)} against ${fmt.num(foreign.brier_base_rate, 4)}.` }),
    ledgerRows.length
      ? table(`your own ledger · ${ledger.forecasts} forecasts · it said ${fmt.pct(ledger.mean_forecast)}, you did ${fmt.pct(ledger.observed)} · brier ${fmt.num(ledger.brier, 3)}`,
          ["skill", "question", "forecast P(correct)", "what happened"], ledgerRows, { numeric: [2] })
      : h("p", { class: "note", text: "Your own ledger is empty: answer a few questions and every forecast will be listed here against what happened." }),
    h("p", { class: "note", text: "Readiness scores in exam-prep products are usually a closed formula. Here every forecast depends only on the answers before it, and can be checked afterwards." }),
    table(`route search · ${data.profiles} random learners per destination · mean states expanded and share of optimal routes`,
      ["destination", "required skills", "A*", "UCS", "BFS", "A* optimal", "greedy optimal", "BFS optimal"], searchRows, { numeric: [1, 2, 3, 4, 5, 6, 7] }),
    h("p", { class: "note", text: "A* and UCS always return the same cost. A* gets there after expanding a fraction of the states, because the heuristic tells it which partial routes cannot win." }),
  ];
}

import { h, fmt, meter, beliefMeters, STATE_NAMES, ACTION_LABEL } from "../ui.js";

const LETTERS = ["a", "b", "c", "d", "e", "f"];
const skillOf = (state, id) => state.skills.find((skill) => skill.id === id);

export function renderDrive(app, actions) {
  const { state, ui } = app;
  const stepClass = `step${ui.stepFresh ? " enter" : ""}`;
  let step;
  if (ui.error) step = failed(ui.error, actions);
  else if (ui.phase === "feedback" && state.last?.action === "practice") step = feedback(app, actions);
  else if (state.done) step = arrived(app);
  else if (state.current.action === "explain") step = lesson(app, actions);
  else step = question(app, actions);
  step.setAttribute("class", `${stepClass} ${step.getAttribute("class") || ""}`.trim());

  return h("div", { class: "drive" },
    journey(app),
    h("div", { class: "cols" }, step, why(app, actions)));
}

function journey(app) {
  const { state, pack, store } = app;
  const scope = new Set(state.readiness.skills);
  const done = state.skills.filter((skill) => skill.status === "completed" && scope.has(skill.id)).length;
  const total = done + state.route.stops.length;
  const current = state.current ? skillOf(state, state.current.skill) : null;
  const progress = current && !state.current.reviewing ? current.belief[2] : 0;
  const position = total === 0 ? 1 : Math.min(1, (done + progress) / total);
  const destination = pack.destinations.find((d) => d.id === store.destination);

  const ticks = [];
  for (let i = 0; i <= total; i += 1) {
    const kind = i <= done ? "done" : i === done + 1 ? "now" : "";
    ticks.push(h("span", { class: `tick ${kind}`, style: { left: `${total ? (i / total) * 100 : 100}%` } }));
  }
  const pass = state.readiness.pass_probability;
  return h("section", { class: "journey", "aria-label": "Route progress" },
    h("div", { class: "journey-facts label" },
      h("span", {}, state.done ? "arrived" : h("b", { text: `stop ${Math.min(done + 1, total)} of ${total}` })),
      h("span", {}, h("b", { class: "num", text: `≈ ${fmt.min(state.route.eta_minutes)}` }), " left"),
      h("span", { title: `Chance to score ${fmt.pct(state.readiness.pass_fraction)} or more, one question per skill` },
        h("b", { class: "num", text: fmt.pct(pass) }), ` chance to pass if the exam were today`)),
    h("div", { class: "scale", role: "img", "aria-label": `${done} of ${total} stops completed` },
      ticks,
      here(app, position)),
    h("div", { class: "scale-ends label" },
      h("span", { text: "start" }),
      h("span", { text: destination ? destination.name.toLowerCase() : "destination" })));
}

function here(app, position) {
  const from = app.ui.lastPosition ?? position;
  const node = h("span", { class: "here", style: { "--at": from.toFixed(4) } });
  app.ui.lastPosition = position;
  if (from !== position) requestAnimationFrame(() => requestAnimationFrame(() => node.style.setProperty("--at", position.toFixed(4))));
  return node;
}

function stepLabel(app, kind) {
  const { state } = app;
  const skill = skillOf(state, state.current.skill);
  const review = state.current.reviewing ? " · review" : "";
  return h("p", { class: "label", text: `${skill.name.toLowerCase()} · ${kind}${review}` });
}

function question(app, actions) {
  const { state, ui } = app;
  const { item } = state.current;
  const sure = h("button", { class: "btn primary", type: "button", id: "sure", text: "I'm sure", disabled: ui.selected === null, onClick: () => actions.answer(true) });
  const unsure = h("button", { class: "btn", type: "button", id: "unsure", text: "Not sure", disabled: ui.selected === null, onClick: () => actions.answer(false) });

  const select = (index) => {
    ui.selected = index;
    options.querySelectorAll(".option").forEach((node, n) => node.setAttribute("aria-checked", String(n === index)));
    sure.disabled = unsure.disabled = false;
  };
  const options = h("div", { class: "options", role: "radiogroup", "aria-label": "Answer options" },
    item.options.map((text, index) =>
      h("button", { class: "option", type: "button", role: "radio", "aria-checked": String(ui.selected === index), onClick: () => select(index) },
        h("span", { class: "key" }, h("span", { text: LETTERS[index] })),
        h("span", { class: "text", text }))));
  options.select = select;

  return h("section", { "aria-live": "polite" },
    stepLabel(app, `question ${state.current.steps + 1}`),
    h("p", { class: "prompt", text: item.prompt }),
    options,
    h("div", { class: "actions" }, sure, unsure,
      state.current.reviewing ? null
        : h("button", { class: "textlink label", type: "button", text: "show me the lesson first", onClick: actions.askLesson })),
    h("p", { class: "label hint", text: "keys: 1–4 choose · s sure · n not sure" }));
}

function feedback(app, actions) {
  const { state } = app;
  const last = state.last;
  const skill = skillOf(state, last.skill);
  const options = h("div", { class: "options" },
    last.options.map((text, index) => {
      const isAnswer = index === last.answer;
      const isChoice = index === last.choice;
      let tag = null;
      if (isAnswer && isChoice) tag = h("span", { class: "mark ok", text: "your answer, correct" });
      else if (isAnswer) tag = h("span", { class: "mark ok", text: "correct answer" });
      else if (isChoice) tag = h("span", { class: "mark bad", text: "your answer" });
      return h("div", { class: `option${isAnswer || isChoice ? "" : " dim"}` },
        h("span", { class: "key" }, h("span", { text: LETTERS[index] })),
        h("span", { class: "text", text }), tag);
    }));

  let headline = last.correct ? "Correct." : "Not yet.";
  let note = null;
  if (!last.correct && last.sure) note = "You were sure of this one. Confident errors are the ones that stick best once corrected, so read the reason closely.";
  if (last.correct && !last.sure) note = "Right, though you were not sure. One more question on this skill will make it hold.";

  const before = last.belief_before[2];
  const after = last.belief_after[2];
  const passed = (last.advanced || []).map((event) => skillOf(state, event.skill).name);
  const button = h("button", { class: "btn primary", type: "button", id: "continue", text: state.done ? "See where you arrived" : "Continue", onClick: actions.next });
  queueMicrotask(() => button.focus({ preventScroll: true }));

  return h("section", {},
    h("p", { class: "label", text: `${skill.name.toLowerCase()} · your answer` }),
    h("p", { class: "prompt", text: last.prompt }),
    options,
    h("div", { class: "verdict", role: "status" },
      h("h3", { text: headline }),
      h("p", { text: last.why }),
      note ? h("p", { class: "note", text: note }) : null,
      h("p", { class: "label delta num", text: `p(mastered) ${fmt.p(before)} → ${fmt.p(after)}` }),
      passed.map((name) => h("p", {}, h("span", { class: "mark ok", text: `checkpoint passed: ${name.toLowerCase()}` })))),
    h("div", { class: "actions" }, button));
}

function lesson(app, actions) {
  const { state } = app;
  const skill = skillOf(state, state.current.skill);
  const content = state.current.lesson;
  const button = h("button", { class: "btn primary", type: "button", id: "continue", text: "Got it, test me", onClick: actions.lessonRead });
  return h("section", {},
    stepLabel(app, "lesson"),
    h("h2", { text: skill.name }),
    h("div", { class: "lesson" },
      h("div", {}, h("span", { class: "label", text: "the idea" }), h("p", { text: content.idea })),
      h("div", {}, h("span", { class: "label", text: "worked example" }), h("p", { text: content.example })),
      h("div", {}, h("span", { class: "label", text: "common trap" }), h("p", { text: content.trap }))),
    h("div", { class: "actions" }, button));
}

function arrived(app) {
  const { state, pack, store } = app;
  const destination = pack.destinations.find((d) => d.id === store.destination);
  const { sure, unsure } = state.calibration;
  return h("section", { class: "arrived" },
    h("p", { class: "label", text: "you have arrived" }),
    h("h1", {}, "You reached", h("br"), h("span", { class: "acc", text: destination ? destination.name : "your destination" }), "."),
    h("div", { class: "rows facts" },
      fact("questions answered", String(state.answered)),
      fact("study time by the model's clock", fmt.min(state.elapsed_minutes)),
      fact(`chance to score ${fmt.pct(state.readiness.pass_fraction)} or more today`, fmt.pct(state.readiness.pass_probability)),
      sure.n + unsure.n > 0 ? fact("right when sure / right when not sure", `${sure.correct} of ${sure.n} / ${unsure.correct} of ${unsure.n}`) : null),
    h("div", { class: "actions" },
      h("a", { class: "btn primary", href: "#/", text: "Choose a new destination" }),
      h("a", { class: "textlink label", href: "#/engine", text: "see how it decided" })));
}

function fact(name, value) {
  return h("div", { style: { display: "flex", "justify-content": "space-between", gap: "16px" } },
    h("span", { text: name }), h("span", { class: "label num", text: value }));
}

function failed(message, actions) {
  return h("section", { class: "error", role: "alert" },
    h("span", { class: "mark bad", text: "engine unreachable" }),
    h("p", { text: message }),
    h("p", { class: "note", text: "Nothing is lost: your answers are kept in this browser." }),
    h("button", { class: "btn", type: "button", text: "Try again", onClick: actions.retry }));
}

function why(app, actions) {
  const { state, ui, store } = app;
  const showingAnswer = ui.phase === "feedback" && state.last?.action === "practice";
  const located = showingAnswer ? skillOf(state, state.last.skill) : state.current ? skillOf(state, state.current.skill) : null;
  const blocks = [];

  if (located) {
    const belief = showingAnswer ? state.last.belief_after : located.belief;
    blocks.push(h("section", {},
      h("h3", {}, h("span", { text: "where you are" }), h("span", { text: "hmm" })),
      h("p", { class: "skillname", style: { color: "var(--fg)", "margin-top": "0" }, text: located.name }),
      beliefMeters(belief),
      h("p", { text: `Estimated from ${located.steps} ${located.steps === 1 ? "step" : "steps"} on this skill. Chance the next answer is right: ${fmt.p(located.p_correct)}.` })));
  }

  if (state.current) {
    const { values, action, reason } = state.current;
    const low = -15;
    const high = 10;
    blocks.push(h("section", {},
      h("h3", {}, h("span", { text: showingAnswer ? `next: ${skillOf(state, state.current.skill).short.toLowerCase()}` : "why this step" }), h("span", { text: "mdp" })),
      Object.entries(values).map(([name, value]) =>
        meter(ACTION_LABEL[name], (value - low) / (high - low), { shown: fmt.num(value), chosen: name === action })),
      h("p", { text: reason })));
  }

  const stops = state.route.stops;
  if (stops.length) {
    const more = stops.length - 5;
    blocks.push(h("section", {},
      h("h3", {}, h("span", { text: "the route" }), h("span", { text: "a*" })),
      h("ol", { class: "stops" }, stops.slice(0, 5).map((stop, index) =>
        h("li", { class: index === 0 ? "now" : null },
          h("span", { class: "label n num", text: String(index + 1).padStart(2, "0") }),
          h("span", { class: "title", text: skillOf(state, stop.skill).short }),
          h("span", { class: "label num", text: fmt.min(stop.minutes) })))),
      h("p", { text: `${more > 0 ? `${more} more stops after these. ` : ""}Cheapest of all valid orders: A* checked ${state.route.search.expanded} partial routes to prove it.` }),
      state.route.detour_minutes > 0.05 ? h("p", { text: `Your detour adds ${fmt.min(state.route.detour_minutes)}.` }) : null,
      store.pin ? h("button", { class: "textlink label", type: "button", text: "back to the planned route", onClick: actions.unpin }) : null));
  }

  const { sure, unsure } = state.calibration;
  if (sure.n + unsure.n >= 3) {
    blocks.push(h("section", {},
      h("h3", {}, h("span", { text: "your confidence" }), h("span", { text: "so far" })),
      meter("when sure", sure.n ? sure.correct / sure.n : 0, { shown: `${sure.correct}/${sure.n}` }),
      meter("when not", unsure.n ? unsure.correct / unsure.n : 0, { shown: `${unsure.correct}/${unsure.n}` }),
      h("p", { text: "Share of correct answers. A wide gap means your sense of what you know is accurate." })));
  }
  const ledger = state.calibration;
  if (ledger.forecasts >= 3) {
    blocks.push(h("section", {},
      h("h3", {}, h("span", { text: "is the tutor honest?" }), h("span", { text: `${ledger.forecasts} forecasts` })),
      meter("it said", ledger.mean_forecast, { shown: fmt.pct(ledger.mean_forecast) }),
      meter("you did", ledger.observed, { shown: fmt.pct(ledger.observed) }),
      h("p", { text: "Before every answer the tutor forecasts the chance you get it right. Here is its average forecast against what happened. The full ledger is in the engine room." })));
  }
  return h("aside", { class: "why", "aria-label": "Why this step" }, blocks);
}

export function driveKey(event, app, actions) {
  const { state, ui } = app;
  const typing = ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement?.tagName);
  if (typing || ui.busy || ui.phase !== "step" || !state.current?.item) return;
  const key = event.key.toLowerCase();
  const count = state.current.item.options.length;
  const index = "1234".includes(key) && key ? Number(key) - 1 : LETTERS.indexOf(key);
  const options = document.querySelector(".options");
  if (key.length === 1 && index >= 0 && index < count && key !== "s" && options?.select) {
    options.select(index);
    event.preventDefault();
  } else if (key === "s" && ui.selected !== null) {
    actions.answer(true);
  } else if (key === "n" && ui.selected !== null) {
    actions.answer(false);
  }
}

// Controller: owns the state, talks to the engine, picks the view.

import { api } from "./api.js";
import * as storage from "./store.js";
import { h, mount, toast } from "./ui.js";
import { renderStart } from "./views/start.js";
import { renderDrive, driveKey } from "./views/drive.js";
import { renderMap } from "./views/map.js";
import { renderEngine } from "./views/engine.js";

const app = {
  store: storage.load(),
  pack: null,
  model: null,
  state: null,
  evidence: null,
  ui: {
    view: "start", phase: "step", selected: null, busy: false, error: null, lessonAsked: false,
    mapSelected: null, engineTab: "hmm", inspect: null, compare: null, eraseArmed: false, choice: null,
    fresh: true, stepFresh: true,  // play the entrance motion only when a screen or a step is new
  },
};

const root = document.getElementById("view");
const VIEWS = ["drive", "map", "engine"];

// ---------------------------------------------------------------- engine calls

async function refresh({ lesson = false } = {}) {
  const { store, ui } = app;
  ui.busy = true;
  ui.error = null;
  try {
    const state = await api.state({
      targets: store.targets, history: store.history, pin: store.pin, lesson, inspect: ui.inspect,
    });
    if (state.append.length) {
      store.history.push(...state.append);
      const names = state.append.map((event) => skillName(event.skill));
      if (ui.phase !== "feedback") toast(`checkpoint passed: ${names.join(", ")}`);  // feedback shows it inline
      if (state.append.some((event) => event.skill === store.pin)) store.pin = null;
    }
    app.state = state;
    ui.stepFresh = true;
    ui.lessonAsked = lesson;
    ui.compare = null;
    storage.save(store);
  } catch (error) {
    ui.error = error.message;
  } finally {
    ui.busy = false;
  }
  render();
}

const skillName = (id) => app.pack.skills.find((skill) => skill.id === id)?.name ?? id;

const actions = {
  retry: () => refresh(),

  choose(destinationId) {
    const destination = app.pack.destinations.find((d) => d.id === destinationId);
    if (!destination) return;
    Object.assign(app.store, { destination: destination.id, targets: destination.targets, pin: null });
    Object.assign(app.ui, { phase: "step", selected: null, inspect: null, mapSelected: null });
    storage.save(app.store);
    go("drive");
    refresh();
  },

  answer(sure) {
    const current = app.state?.current;
    if (!current?.item || app.ui.selected === null || app.ui.busy) return;
    app.store.history.push({
      skill: current.skill, action: "practice", item: current.item.id, choice: app.ui.selected, sure,
    });
    app.ui.phase = "feedback";
    refresh();
  },

  lessonRead() {
    const current = app.state?.current;
    if (!current || app.ui.busy) return;
    app.store.history.push({ skill: current.skill, action: "explain" });
    app.ui.phase = "step";
    app.ui.selected = null;
    refresh();
  },

  askLesson: () => refresh({ lesson: true }),

  next() {
    Object.assign(app.ui, { phase: "step", selected: null, stepFresh: true });
    render();
  },

  pin(skillId) {
    app.store.pin = skillId;
    Object.assign(app.ui, { phase: "step", selected: null });
    go("drive");
    refresh();
  },

  unpin() {
    app.store.pin = null;
    Object.assign(app.ui, { phase: "step", selected: null });
    refresh();
  },

  inspect(skillId) {
    app.ui.inspect = skillId;
    refresh();
  },

  async compare() {
    try {
      app.ui.compare = (await api.compare({ targets: app.store.targets, history: app.store.history })).results;
    } catch (error) {
      app.ui.compare = { error: error.message };
    }
    render();
  },

  async loadEvidence() {
    if (app.evidence) return;
    try { app.evidence = await api.evidence(); } catch (error) { app.evidence = { error: error.message }; }
    render();
  },

  erase() {
    if (!app.ui.eraseArmed) {
      app.ui.eraseArmed = true;
      render();
      return;
    }
    storage.erase(app.store);
    app.state = null;
    Object.assign(app.ui, { eraseArmed: false, phase: "step", selected: null, choice: null, inspect: null });
    go("start");
    render();
  },

  set(patch) {
    Object.assign(app.ui, patch);
    render();
  },
};

// ---------------------------------------------------------------- routing and rendering

function go(view) {
  const hash = view === "start" ? "#/" : `#/${view}`;
  if (location.hash !== hash) location.hash = hash;
  else route();
}

function route() {
  const requested = location.hash.replace(/^#\//, "") || "start";
  const hasRoute = app.store.targets.length > 0;
  app.ui.view = VIEWS.includes(requested) && hasRoute ? requested : "start";
  Object.assign(app.ui, { eraseArmed: false, fresh: true, stepFresh: true });
  render();
  root.focus({ preventScroll: true });
  window.scrollTo({ top: 0 });
  if (app.ui.view !== "start" && !app.state && !app.ui.busy) refresh();
}

function render() {
  if (!app.pack) return;
  draw();
  app.ui.fresh = app.ui.stepFresh = false;
}

function draw() {
  const { ui, state } = app;
  const dock = document.getElementById("dock");
  dock.hidden = ui.view === "start";
  for (const link of dock.querySelectorAll("a")) {
    if (link.dataset.view === ui.view) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
  const index = Math.max(0, VIEWS.indexOf(ui.view));
  document.getElementById("dock-indicator").style.transform = `translateX(${index * 100}%)`;

  const destination = app.pack.destinations.find((d) => d.id === app.store.destination);
  document.getElementById("top-where").textContent =
    ui.view === "start" || !destination ? "a gps for learning" : `to ${destination.name.toLowerCase()}`;

  if (ui.view === "start") return mount(root, renderStart(app, actions));
  if (ui.error && !state) return mount(root, errorBlock(ui.error));
  if (!state) return mount(root, h("p", { class: "label loading", text: "planning your route" }));
  if (ui.view === "drive") return mount(root, renderDrive(app, actions));
  if (ui.view === "map") return mount(root, renderMap(app, actions));
  return mount(root, renderEngine(app, actions));
}

function errorBlock(message) {
  return h("div", { class: "error", role: "alert" },
    h("span", { class: "mark bad", text: "engine unreachable" }),
    h("p", { text: message }),
    h("button", { class: "btn", type: "button", text: "Try again", onClick: actions.retry }));
}

// ---------------------------------------------------------------- theme

function applyTheme() {
  const button = document.getElementById("theme");
  const system = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  const active = app.store.theme || system;
  if (app.store.theme) document.documentElement.dataset.theme = app.store.theme;
  else delete document.documentElement.dataset.theme;
  button.textContent = active === "dark" ? "light" : "dark";
  button.setAttribute("aria-label", `Switch to the ${button.textContent} theme`);
}

document.getElementById("theme").addEventListener("click", () => {
  const system = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  const active = app.store.theme || system;
  app.store.theme = active === "dark" ? "light" : "dark";
  storage.save(app.store);
  applyTheme();
});

// ---------------------------------------------------------------- start

window.addEventListener("hashchange", route);
window.addEventListener("keydown", (event) => {
  if (event.metaKey || event.ctrlKey || event.altKey) return;
  if (app.ui.view === "drive" && app.state) driveKey(event, app, actions);
});

async function boot() {
  applyTheme();
  try {
    [app.pack, app.model] = await Promise.all([api.pack(), api.model()]);
  } catch (error) {
    mount(root, h("div", { class: "error", role: "alert" },
      h("span", { class: "mark bad", text: "engine unreachable" }),
      h("p", { text: error.message }),
      h("button", { class: "btn", type: "button", text: "Try again", onClick: boot })));
    return;
  }
  if (!app.pack.destinations.some((d) => d.id === app.store.destination)) app.store.targets = [];
  route();
}

boot();

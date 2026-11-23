import { h, fmt, beliefMeters } from "../ui.js";

const COL = 150;
const ROW = 92;
const LEFT = 64;
const TOP = 34;
const BOX = 18;

const STATUS_TEXT = {
  completed: ["ok", "completed"],
  current: ["info", "you are here"],
  route: ["", "on your route"],
  optional: ["", "helpful, not on the route"],
  off: ["", "not needed for this destination"],
};

export function renderMap(app, actions) {
  const { state, ui } = app;
  const byId = Object.fromEntries(state.skills.map((skill) => [skill.id, skill]));
  const order = Object.fromEntries(state.route.stops.map((stop, index) => [stop.skill, index + 1]));
  const selectedId = ui.mapSelected && byId[ui.mapSelected] ? ui.mapSelected : state.current?.skill ?? state.skills[0].id;
  const at = (skill) => [LEFT + skill.x * COL, TOP + skill.y * ROW];
  const active = (skill) => skill.status !== "off" && skill.status !== "optional";
  const columns = Math.max(...state.skills.map((skill) => skill.x));
  const rows = Math.max(...state.skills.map((skill) => skill.y));

  const edges = [];
  for (const skill of state.skills) {
    for (const [kind, parents] of [["hard", skill.hard], ["soft", skill.soft]]) {
      for (const parentId of parents) {
        const [x1, y1] = at(byId[parentId]);
        const [x2, y2] = at(skill);
        const mid = (x1 + x2) / 2;
        const on = active(skill) && active(byId[parentId]) ? " on" : "";
        edges.push(h("path", { class: `edge ${kind}${on}`, d: `M${x1 + BOX / 2} ${y1} C${mid} ${y1} ${mid} ${y2} ${x2 - BOX / 2} ${y2}` }));
      }
    }
  }

  const nodes = state.skills.map((skill) => {
    const [x, y] = at(skill);
    const mastered = skill.status === "completed" ? 1 : skill.belief[2];
    const fill = Math.max(0, (BOX - 2) * mastered);
    const description = `${skill.name}: ${STATUS_TEXT[skill.status][1]}, probability mastered ${fmt.p(skill.belief[2])}`;
    const choose = () => actions.set({ mapSelected: skill.id });
    return h("g", {
      class: `node ${skill.status}${skill.id === selectedId ? " selected" : ""}`, tabindex: "0", role: "button", "aria-label": description,
      onClick: choose, onKeydown: (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); choose(); } },
    },
      h("title", { text: description }),
      h("rect", { class: "hit", x: x - 54, y: y - 22, width: 108, height: 62 }),
      h("rect", { class: "ring", x: x - BOX / 2 - 5, y: y - BOX / 2 - 5, width: BOX + 10, height: BOX + 10 }),
      h("rect", { class: "box", x: x - BOX / 2, y: y - BOX / 2, width: BOX, height: BOX }),
      h("rect", { class: "fill", x: x - BOX / 2 + 1, y: y + BOX / 2 - 1 - fill, width: BOX - 2, height: fill }),
      order[skill.id] ? h("text", { class: "order", x: x + BOX / 2 + 6, y: y - 6, text: String(order[skill.id]).padStart(2, "0") }) : null,
      h("text", { x, y: y + BOX / 2 + 18, "text-anchor": "middle", text: skill.short.toLowerCase() }));
  });

  const svg = h("svg", {
    class: "map", viewBox: `0 0 ${LEFT * 2 + columns * COL} ${TOP + rows * ROW + 56}`, role: "group",
    "aria-label": "Skill map. Each square is a skill; lines are prerequisites.",
  }, edges, nodes);

  const completed = state.skills.filter((skill) => skill.status === "completed").length;
  return h("div", { class: `mapview${ui.fresh ? " enter" : ""}` },
    h("div", { class: "maphead" },
      h("h2", {}, "The map: ", h("span", { class: "acc", text: `${state.route.stops.length} stops` }), " to go"),
      h("span", { class: "label", text: `${completed} completed · ≈ ${fmt.min(state.route.eta_minutes)} left` })),
    h("div", { class: "legend label" },
      legendItem(swatch(0.6), "fill = probability mastered"),
      legendItem(h("svg", { width: 26, height: 10 }, h("path", { class: "edge on", d: "M0 5 L26 5", style: { stroke: "var(--tick)", fill: "none" } })), "required first"),
      legendItem(h("svg", { width: 26, height: 10 }, h("path", { d: "M0 5 L26 5", style: { stroke: "var(--tick)", fill: "none", "stroke-dasharray": "3 4" } })), "helps, can be skipped"),
      h("span", {}, h("span", { class: "num", style: { color: "var(--fg)" }, text: "01" }), "order on your route")),
    h("div", { class: "mapscroll" }, svg),
    detail(app, byId[selectedId], byId, order, actions));
}

function swatch(share) {
  return h("svg", { width: 14, height: 14 },
    h("rect", { x: 0.5, y: 0.5, width: 13, height: 13, style: { fill: "none", stroke: "var(--tick)" } }),
    h("rect", { x: 1.5, y: 13 - 12 * share, width: 11, height: 12 * share - 0.5, style: { fill: "var(--fg)" } }));
}

function legendItem(icon, text) {
  return h("span", {}, icon, text);
}

function detail(app, skill, byId, order, actions) {
  const { store } = app;
  const [kind, text] = STATUS_TEXT[skill.status];
  const names = (ids) => ids.map((id) => byId[id].short).join(", ");
  const facts = [];
  if (skill.hard.length) facts.push(`Needs ${names(skill.hard)} first.`);
  if (skill.soft.length) facts.push(`Goes faster after ${names(skill.soft)}.`);
  if (!skill.hard.length && !skill.soft.length) facts.push("No prerequisites: a possible starting point.");
  if (order[skill.id]) facts.push(`Stop ${order[skill.id]} on your route, about ${fmt.min(skill.minutes)}.`);

  let action = null;
  if (skill.status === "completed") {
    action = h("button", { class: "btn", type: "button", text: "Review this skill", onClick: () => actions.pin(skill.id) });
  } else if (skill.locked) {
    action = h("span", { class: "mark warn", text: "locked: finish its prerequisites first" });
  } else if (skill.status !== "current" || store.pin) {
    action = h("button", { class: "btn", type: "button", text: "Study this now", onClick: () => actions.pin(skill.id) });
  } else {
    action = h("a", { class: "btn primary", href: "#/drive", text: "Continue here" });
  }

  return h("div", { class: "detail" },
    h("div", {},
      h("span", { class: `mark ${kind}`, text: text }),
      h("h3", { text: skill.name }),
      h("p", { text: `Week ${skill.week}. ${facts.join(" ")}` }),
      action),
    h("div", {},
      h("span", { class: "label", text: `belief after ${skill.steps} ${skill.steps === 1 ? "step" : "steps"}` }),
      beliefMeters(skill.belief)));
}

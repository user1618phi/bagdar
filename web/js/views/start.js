// Start: one question ("where to?"), one primary button.

import { h } from "../ui.js";

export function renderStart(app, actions) {
  const { pack, store, ui } = app;
  const chosen = ui.choice ?? store.destination ?? pack.destinations[0].id;
  const answered = store.history.filter((event) => event.action === "practice").length;
  const resuming = store.targets.length > 0 && chosen === store.destination;

  const list = h("div", { class: "destinations", role: "radiogroup", "aria-label": "Destination" },
    pack.destinations.map((destination) =>
      h("button", {
        class: "destination", type: "button", role: "radio",
        "aria-checked": String(destination.id === chosen),
        onClick: () => actions.set({ choice: destination.id }),
        onDblclick: () => actions.choose(destination.id),
      },
        h("span", { class: "key", "aria-hidden": "true" }),
        h("span", {},
          h("span", { class: "name", text: destination.name }),
          h("span", { class: "note", text: destination.note })),
        h("span", { class: "label", text: `${destination.targets.length} ${destination.targets.length === 1 ? "target" : "targets"}` }))));

  return h("div", { class: `start${ui.fresh ? " enter" : ""}` },
    h("p", { class: "label", text: `${pack.title.toLowerCase()} · ${pack.skills.length} skills · ${pack.items} questions` }),
    h("h1", {}, "Where do you", h("br"), "want to ", h("span", { class: "acc", text: "get to" }), "?"),
    list,
    h("div", { class: "start-actions" },
      h("button", { class: "btn primary", type: "button", text: resuming ? "Continue the route" : "Plan my route", onClick: () => actions.choose(chosen) }),
      answered > 0 ? h("span", { class: "label", text: `${answered} answers kept on this device` }) : null,
      answered > 0 ? h("button", { class: "textlink label", type: "button", text: ui.eraseArmed ? "press again to erase everything" : "erase progress", onClick: actions.erase }) : null),
    h("div", { class: "ruler", style: { "margin-top": "var(--space-12)" }, role: "presentation" }),
    h("div", { class: "pillars" },
      pillar("01 · locate", "A hidden Markov model reads your answers and estimates what you really know, as a probability."),
      pillar("02 · route", "A* search finds the shortest path through the prerequisite map from where you are to where you want to be."),
      pillar("03 · steer", "A Markov decision process picks each next step: a short lesson, a question, or moving on.")));
}

function pillar(label, text) {
  return h("div", {}, h("span", { class: "label", text: label }), h("p", { text }));
}

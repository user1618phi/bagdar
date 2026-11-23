// Small DOM helpers. No framework: the whole app is a few pure render functions.

const SVG_NS = "http://www.w3.org/2000/svg";
const SVG_TAGS = new Set(["svg", "g", "path", "rect", "text", "line", "circle", "title"]);

/** Create an element. Props: class, text, html-free attributes, on<Event> handlers, style object. */
export function h(tag, props = {}, ...children) {
  const node = SVG_TAGS.has(tag) ? document.createElementNS(SVG_NS, tag) : document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") node.setAttribute("class", value);
    else if (key === "text") node.textContent = value;
    else if (key === "style") for (const [name, v] of Object.entries(value)) node.style.setProperty(name, v);
    else if (key.startsWith("on")) node.addEventListener(key.slice(2).toLowerCase(), value);
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return node;
}

export const fmt = {
  p: (x) => x.toFixed(2),
  p3: (x) => x.toFixed(3),
  pct: (x) => `${Math.round(x * 100)}%`,
  min: (x) => (x < 0.5 ? "0 min" : `${Math.round(x)} min`),
  num: (x, digits = 2) => x.toFixed(digits),
  signed: (x) => `${x >= 0 ? "+" : "−"}${Math.abs(x).toFixed(2)}`,
  vector: (v, digits = 2) => `[${v.map((x) => x.toFixed(digits)).join(", ")}]`,
};

export const STATE_NAMES = ["unknown", "fragile", "mastered"];
export const ACTION_LABEL = { explain: "lesson", practice: "question", advance: "move on" };
export const OBSERVATION_LABEL = {
  correct_sure: "correct, sure",
  correct_unsure: "correct, not sure",
  wrong_unsure: "wrong, not sure",
  wrong_sure: "wrong, sure",
};

/** A row with a name, a thin bar and a number: the only "chart" the app uses. */
export function meter(name, value, { kind = "", max = 1, shown = null, chosen = false } = {}) {
  const share = Math.max(0, Math.min(1, value / max));
  return h("div", { class: `meter${chosen ? " chosen" : ""}` },
    h("span", { class: "label name", text: name }),
    h("span", { class: `bar ${kind}`, role: "presentation" }, h("i", { style: { "--v": share.toFixed(4) } })),
    h("span", { class: "label value num", text: shown ?? fmt.p(value) }));
}

/** The three-state belief of the HMM as three labelled meters. */
export function beliefMeters(belief) {
  return STATE_NAMES.map((name, index) => meter(name, belief[index], { kind: name }));
}

export function table(caption, head, rows, { numeric = [], best = -1 } = {}) {
  return h("div", { class: "tablewrap" },
    h("table", {},
      caption ? h("caption", { text: caption }) : null,
      h("thead", {}, h("tr", {}, head.map((text, c) => h("th", { class: numeric.includes(c) ? "n" : null, scope: "col", text })))),
      h("tbody", {}, rows.map((row, r) =>
        h("tr", { class: r === best ? "best" : null }, row.map((cell, c) =>
          h("td", { class: numeric.includes(c) ? "n" : null }, cell)))))));
}

let toastTimer = null;
export function toast(message) {
  const node = document.getElementById("toast");
  node.textContent = "";
  node.append(h("span", { class: "mark ok", text: message }));
  node.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { node.hidden = true; }, 3200);
}

export function mount(root, node) {
  root.replaceChildren(node);
}

const KEY = "meje.v1";

const blank = () => ({ destination: null, targets: [], history: [], pin: null, theme: null });

export function load() {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || "null");
    if (saved && Array.isArray(saved.history) && Array.isArray(saved.targets)) return { ...blank(), ...saved };
  } catch {}
  return blank();
}

export function save(store) {
  try { localStorage.setItem(KEY, JSON.stringify(store)); } catch {}
}

export function erase(store) {
  Object.assign(store, blank(), { theme: store.theme });
  save(store);
}

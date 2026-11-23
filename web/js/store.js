// The learner's data lives in this browser only: destination, history of events and theme.
// localStorage can be unavailable (private mode), so every access is guarded and the app
// still works without it for the length of the visit.

const KEY = "meje.v1";

const blank = () => ({ destination: null, targets: [], history: [], pin: null, theme: null });

export function load() {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || "null");
    if (saved && Array.isArray(saved.history) && Array.isArray(saved.targets)) return { ...blank(), ...saved };
  } catch { /* fall through to a blank store */ }
  return blank();
}

export function save(store) {
  try { localStorage.setItem(KEY, JSON.stringify(store)); } catch { /* keep working in memory */ }
}

export function erase(store) {
  Object.assign(store, blank(), { theme: store.theme });
  save(store);
}

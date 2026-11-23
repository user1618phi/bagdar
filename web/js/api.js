// Talks to the Python engine. Every call either returns data or throws an Error with a message
// that can be shown to the learner as it is.

async function request(path, body) {
  let response;
  try {
    response = await fetch(path, body === undefined ? {} : {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error("Can't reach the engine. Check that `python -m meje` is still running.");
  }
  let data = null;
  try { data = await response.json(); } catch { /* handled below */ }
  if (!response.ok || data === null) {
    throw new Error((data && data.error) || `The engine answered with an error (${response.status}).`);
  }
  return data;
}

export const api = {
  pack: () => request("/api/pack"),
  model: () => request("/api/model"),
  evidence: () => request("/api/evidence"),
  state: (body) => request("/api/state", body),
  compare: (body) => request("/api/compare", body),
};

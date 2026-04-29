// Minimal pub/sub state store.
const listeners = new Map();
const stateData = {
  lang: "id",
  lastResult: null,
  lastSourceText: "",
  spotifyConnected: false,
  spotifyExpiresAt: 0,
};

export function getState(key) {
  return stateData[key];
}

export function setState(key, value) {
  stateData[key] = value;
  const subs = listeners.get(key);
  if (subs) for (const fn of subs) fn(value);
}

export function subscribe(key, fn) {
  if (!listeners.has(key)) listeners.set(key, new Set());
  listeners.get(key).add(fn);
  return () => listeners.get(key)?.delete(fn);
}

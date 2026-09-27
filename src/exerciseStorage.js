/** Shared localStorage-backed exercise session log, used by both the
 * Exercises tab (guided sessions + manual logging) and the Insights tab
 * (summary + its own "+ Add exercise" shortcut), so the two stay in sync. */

const KEY = 'mf_exercise_sessions';

function load() { try { return JSON.parse(localStorage.getItem(KEY)) ?? []; } catch { return []; } }
function save(list) { localStorage.setItem(KEY, JSON.stringify(list)); }

export function loadSessions() { return load(); }

export function logSession({ name, exerciseId = null, minutes = null, source, timestamp }) {
  const entry = { id: Date.now(), exerciseId, name, minutes, source, timestamp: timestamp || Date.now() };
  const updated = [entry, ...load()];
  save(updated);
  return updated;
}

export function deleteSession(id) {
  const updated = load().filter(s => s.id !== id);
  save(updated);
  return updated;
}

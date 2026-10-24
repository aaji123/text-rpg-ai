const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";

/** Keep JSON errors readable so UI components can show actionable feedback. */
async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "The local game server could not complete the request.");
  return data;
}

export const api = {
  stories: () => request("/stories"),
  createStory: (story) => request("/stories", { method: "POST", body: JSON.stringify(story) }),
  brainstorm: (idea, worldSettings) => request("/stories/brainstorm", { method: "POST", body: JSON.stringify({ idea, ...worldSettings }) }),
  loadStory: (id) => request(`/stories/${encodeURIComponent(id)}`),
  sendMessage: (id, message) => request(`/stories/${encodeURIComponent(id)}/chat`, { method: "POST", body: JSON.stringify({ message }) }),
  rollDice: (id, notation) => request(`/stories/${encodeURIComponent(id)}/dice`, { method: "POST", body: JSON.stringify({ notation }) }),
  saveSettings: (id, settings) => request(`/stories/${encodeURIComponent(id)}/settings`, { method: "PUT", body: JSON.stringify(settings) }),
};

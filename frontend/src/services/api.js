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
  generateExample: (field, worldSettings) => request("/stories/example", { method: "POST", body: JSON.stringify({ field, ...worldSettings }) }),
  loadStory: (id) => request(`/stories/${encodeURIComponent(id)}`),
  beginStory: (id) => request(`/stories/${encodeURIComponent(id)}/begin`, { method: "POST" }),
  sendMessage: (id, message) => request(`/stories/${encodeURIComponent(id)}/chat`, { method: "POST", body: JSON.stringify({ message }) }),
  recapStory: (id) => request(`/stories/${encodeURIComponent(id)}/recap`, { method: "POST" }),
  rollDice: (id, notation) => request(`/stories/${encodeURIComponent(id)}/dice`, { method: "POST", body: JSON.stringify({ notation }) }),
  saveSettings: (id, settings) => request(`/stories/${encodeURIComponent(id)}/settings`, { method: "PUT", body: JSON.stringify(settings) }),
  importStory: async (file) => {
    const response = await fetch(`${API_BASE}/stories/import`, { method: "POST", headers: { "Content-Type": "application/zip" }, body: file });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "The story archive could not be imported.");
    return data;
  },
  exportStory: async (id) => {
    const response = await fetch(`${API_BASE}/stories/${encodeURIComponent(id)}/export`);
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || "The story could not be exported.");
    }
    return response.blob();
  },
  deleteStory: (id) => request(`/stories/${encodeURIComponent(id)}`, { method: "DELETE" }),
};

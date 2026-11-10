const BASE = import.meta.env.VITE_API_URL || "/api";

async function req(path, opts) {
  let res;
  try {
    res = await fetch(BASE + path, opts);
  } catch {
    throw new Error("Can't reach the backend. Is the Django server running on port 8000?");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

export const api = {
  documents: () => req("/documents/"),
  upload: (file) => {
    const body = new FormData();
    body.append("file", file);
    return req("/documents/", { method: "POST", body });
  },
  remove: (id) => req(`/documents/${id}/`, { method: "DELETE" }),
  chat: (question) =>
    req("/chat/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }) }),
  history: () => req("/history/"),
};

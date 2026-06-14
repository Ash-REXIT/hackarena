const API_BASE = import.meta.env.VITE_API_URL || "";

async function request(path, options = {}, timeoutMs = 600000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      cache: "no-store",
      headers: {
        ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...options.headers,
      },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || data.message || "Request failed");
    }
    return data;
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error("Request timed out. The local model may still be thinking.");
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  health: () => request("/api/health"),
  chatStatus: () => request("/api/chat/status", {}, 10000),
  chat: (query, requestId) =>
    request("/api/chat", {
      method: "POST",
      body: JSON.stringify({ query, request_id: requestId }),
    }),
  documents: () => request("/api/documents"),
  upload: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/api/documents/upload", { method: "POST", body: form });
  },
  budget: () => request("/api/budget"),
  encoder: () => request("/api/encoder"),
  tools: () => request("/api/tools"),
};

export function formatBytes(bytes) {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function privacyColor(score) {
  if (score >= 90) return "text-accent";
  if (score >= 60) return "text-warn";
  return "text-danger";
}

export function confidenceColor(score) {
  if (score >= 75) return "text-accent";
  if (score >= 45) return "text-warn";
  return "text-danger";
}

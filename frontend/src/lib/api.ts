import { getAccessToken } from "./supabase";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  // Add Supabase auth token if available
  const token = await getAccessToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Merge caller headers
  if (options?.headers) {
    Object.assign(headers, options.headers);
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || `${res.status}`);
  }
  return res.json();
}

export const api = {
  // Dashboard
  getKPIs: () => fetchAPI<any>("/dashboard/kpis"),
  getAlerts: () => fetchAPI<any>("/alerts"),

  // Chat
  chat: (message: string, threadId?: string) =>
    fetchAPI<{ response: string; thread_id: string }>("/chat", {
      method: "POST",
      body: JSON.stringify({ message, thread_id: threadId }),
    }),

  // Decisions
  getDecisions: (limit = 50, offset = 0) =>
    fetchAPI<any>(`/api/decisions?limit=${limit}&offset=${offset}`),
  getDecision: (id: string) => fetchAPI<any>(`/api/decisions/${id}`),

  // Scheduler
  getTasks: (activeOnly = false) =>
    fetchAPI<any>(`/api/scheduler/tasks?active_only=${activeOnly}`),
  getRuns: (limit = 50) => fetchAPI<any>(`/api/scheduler/runs?limit=${limit}`),
  deleteTask: (id: string) =>
    fetchAPI<any>(`/api/scheduler/tasks/${id}`, { method: "DELETE" }),

  // Folders
  getFolders: () => fetchAPI<any>("/api/folders"),
  addFolder: (data: { provider: string; folder_path?: string; display_name: string }) =>
    fetchAPI<any>("/api/folders", { method: "POST", body: JSON.stringify(data) }),
  removeFolder: (id: string) =>
    fetchAPI<any>(`/api/folders/${id}`, { method: "DELETE" }),

  // Files
  getFileTree: () => fetchAPI<any>("/api/files/tree"),
  getFolder: (id: string) => fetchAPI<any>(`/api/files/folder/${id}`),

  // Documents
  getDocuments: (limit = 50) => fetchAPI<any>(`/api/documents?limit=${limit}`),
  getDocument: (id: string) => fetchAPI<any>(`/api/documents/${id}`),

  // Sessions
  getSessions: () => fetchAPI<any>("/api/sessions"),

  // Settings
  getSettings: () => fetchAPI<any>("/api/settings"),

  // Onboarding
  getOnboardingStatus: () => fetchAPI<any>("/api/onboarding/status"),

  // Integrations
  getDriveStatus: () => fetchAPI<any>("/api/integrations/drive/status"),
  getTelegramStatus: () => fetchAPI<any>("/api/integrations/telegram/status"),
};

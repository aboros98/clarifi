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
    fetchAPI<{ response: string; thread_id: string; tools_used?: string[] }>("/chat", {
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
  deleteDocument: (id: string) =>
    fetchAPI<any>(`/api/documents/${id}`, { method: "DELETE" }),
  uploadDocument: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);

    const headers: Record<string, string> = {};
    const token = await getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/documents/upload`,
      { method: "POST", headers, body: formData }
    );
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText);
      throw new Error(text || `${res.status}`);
    }
    return res.json();
  },

  // Sessions
  getSessions: () => fetchAPI<any>("/api/sessions"),

  // Settings
  getSettings: () => fetchAPI<any>("/api/settings"),

  // Onboarding
  getOnboardingStatus: () => fetchAPI<any>("/api/onboarding/status"),
  onboard: (data: {
    companies: { company_name: string; trade_name?: string; tax_id?: string; registration_number?: string; address?: string; city?: string; country_code?: string; bank_accounts?: { iban: string; bank_name: string; currency: string }[] }[];
    user_name: string;
    user_role?: string;
  }) =>
    fetchAPI<any>("/api/onboarding", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  switchCompany: (companyId: string) =>
    fetchAPI<any>(`/api/onboarding/switch-company/${companyId}`, {
      method: "POST",
    }),
  updateProfile: (data: { user_name?: string; user_role?: string }) =>
    fetchAPI<any>("/api/onboarding/profile", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  addCompany: (data: { company_name: string; tax_id?: string; city?: string; registration_number?: string }) =>
    fetchAPI<any>("/api/onboarding/companies", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  removeCompany: (companyId: string) =>
    fetchAPI<any>(`/api/onboarding/companies/${companyId}`, {
      method: "DELETE",
    }),

  // Integrations
  getDriveStatus: () => fetchAPI<any>("/api/integrations/drive/status"),
  getTelegramStatus: () => fetchAPI<any>("/api/integrations/telegram/status"),
};

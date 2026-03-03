const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Token storage
// ---------------------------------------------------------------------------

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

export function saveTokens(access: string, refresh: string) {
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
}

export function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("refresh_token");
}

// ---------------------------------------------------------------------------
// Fetch helper
// ---------------------------------------------------------------------------

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  withAuth = true,
  timeoutMs = 45_000
): Promise<T> {
  const ctrl = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; ctrl.abort(); }, timeoutMs);

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (withAuth) {
    const token = getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(`${API}${path}`, {
      ...options,
      headers,
      signal: options.signal ?? ctrl.signal,
    });
    clearTimeout(timer);

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(res.status, err.detail ?? "Unknown error");
    }

    if (res.status === 204) return undefined as T;
    return res.json();
  } catch (err) {
    clearTimeout(timer);
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === "AbortError") {
      if (timedOut) throw new ApiError(0, "timeout");
      throw err;
    }
    // Network error (server down, CORS, DNS, etc.)
    throw new ApiError(0, "network");
  }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export async function register(email: string, password: string) {
  return apiFetch<{ access_token: string; refresh_token: string }>(
    "/api/v1/auth/register",
    { method: "POST", body: JSON.stringify({ email, password }) },
    false
  );
}

export async function login(email: string, password: string) {
  return apiFetch<{ access_token: string; refresh_token: string }>(
    "/api/v1/auth/login",
    { method: "POST", body: JSON.stringify({ email, password }) },
    false
  );
}

export async function refreshTokens(refresh_token: string) {
  return apiFetch<{ access_token: string; refresh_token: string }>(
    "/api/v1/auth/refresh",
    { method: "POST", body: JSON.stringify({ refresh_token }) },
    false
  );
}

export async function logout() {
  const refresh_token = getRefreshToken();
  if (refresh_token) {
    await apiFetch("/api/v1/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token }),
    }).catch(() => {});
  }
  clearTokens();
}

// ---------------------------------------------------------------------------
// Analysis
// ---------------------------------------------------------------------------

export type AnalysisStatus = "pending" | "running" | "completed" | "failed";

export interface Source {
  url: string;
  title: string;
  snippet: string;
  domain: string;
  retrieved_at: string;
  credibility_tier?: "high" | "medium" | "low" | "unknown";
  credibility_score?: number;
  credibility_note?: string;
}

export interface DebateRound {
  round_number: number;
  researcher_report: string;
  researcher_sources: Source[];
  advocate_challenge: string;
  advocate_counter_sources: Source[];
  judge_continuation_reason?: string;
}

export interface Verdict {
  label: "TRUE" | "FALSE" | "MISLEADING" | "PARTIALLY_TRUE" | "UNVERIFIABLE";
  confidence: number;
  summary: string;
  reasoning: string;
  supporting_sources: Source[];
  contradicting_sources: Source[];
  total_rounds: number;
  processing_time_ms: number;
}

export interface Analysis {
  id: string;
  claim: string;
  created_at: string;
  status: AnalysisStatus;
  debate: DebateRound[];
  verdict?: Verdict;
  llm_provider: string;
  llm_model: string;
  error?: string;
}

export interface AnalysisListResponse {
  items: Analysis[];
  total: number;
  page: number;
  page_size: number;
}

export async function submitAnalysis(body: {
  claim: string;
  llm_provider: string;
  llm_model?: string;
  language: string;
  max_rounds: number;
}) {
  return apiFetch<{ analysis_id: string; status_url: string }>(
    "/api/v1/analysis",
    { method: "POST", body: JSON.stringify(body) }
  );
}

export async function getAnalysis(id: string) {
  return apiFetch<Analysis>(`/api/v1/analysis/${id}`);
}

export async function listAnalyses(page = 1, page_size = 20) {
  return apiFetch<AnalysisListResponse>(
    `/api/v1/analysis?page=${page}&page_size=${page_size}`
  );
}

export async function deleteAnalysis(id: string) {
  return apiFetch<void>(`/api/v1/analysis/${id}`, { method: "DELETE" });
}

export async function resumeAnalysis(id: string) {
  return apiFetch<{ analysis_id: string; status_url: string }>(
    `/api/v1/analysis/${id}/resume`,
    { method: "POST" }
  );
}

// ---------------------------------------------------------------------------
// Providers
// ---------------------------------------------------------------------------

export async function getConfig(): Promise<{ default_provider: string }> {
  return apiFetch<{ default_provider: string }>("/api/v1/config", {}, false);
}

export async function checkHealth(): Promise<void> {
  await apiFetch<{ status: string }>("/api/v1/health", {}, false, 3_000);
}

export async function getOllamaModels(): Promise<string[]> {
  const data = await apiFetch<{ models: string[] }>("/api/v1/providers/ollama/models");
  return data.models;
}

// ---------------------------------------------------------------------------
// Auth / Me
// ---------------------------------------------------------------------------

export interface Me {
  id: string;
  email: string;
  is_admin: boolean;
  is_disabled: boolean;
}

export async function getMe(): Promise<Me> {
  return apiFetch<Me>("/api/v1/auth/me");
}

// ---------------------------------------------------------------------------
// Admin
// ---------------------------------------------------------------------------

export interface AdminUser {
  id: string;
  email: string;
  is_admin: boolean;
  is_disabled: boolean;
  created_at: string;
}

export interface AdminUserListResponse {
  items: AdminUser[];
  total: number;
  page: number;
  page_size: number;
}

export async function adminListUsers(page = 1, page_size = 50): Promise<AdminUserListResponse> {
  return apiFetch<AdminUserListResponse>(`/api/v1/admin/users?page=${page}&page_size=${page_size}`);
}

export async function adminUpdateUser(
  id: string,
  body: { email?: string; password?: string; is_admin?: boolean; is_disabled?: boolean }
): Promise<AdminUser> {
  return apiFetch<AdminUser>(`/api/v1/admin/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function adminDeleteUser(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/admin/users/${id}`, { method: "DELETE" });
}

export async function adminGetStats() {
  return apiFetch<{
    total_users: number;
    total_analyses: number;
    analyses_by_status: Record<string, number>;
    analyses_by_provider: Record<string, number>;
  }>("/api/v1/admin/stats");
}

export function getExportUrl(id: string) {
  const token = getAccessToken();
  return `${API}/api/v1/analysis/${id}/export?token=${token}`;
}

export function streamAnalysis(id: string): EventSource {
  const token = getAccessToken();
  return new EventSource(
    `${API}/api/v1/analysis/${id}/stream`,
    // EventSource doesn't support custom headers; pass token via query param
    // The backend must accept ?token= or we use a workaround (fetch-based SSE)
  );
}

// Fetch-based SSE reader (supports Authorization header)
export async function* streamAnalysisEvents(
  id: string,
  signal?: AbortSignal
): AsyncGenerator<{ event: string; data: unknown }> {
  const token = getAccessToken();
  const res = await fetch(`${API}/api/v1/analysis/${id}/stream`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "text/event-stream",
    },
    signal,
  });

  if (!res.ok) throw new ApiError(res.status, "Stream failed");
  if (!res.body) return;

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("event:")) {
        currentEvent = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        const raw = line.slice(5).trim();
        try {
          yield { event: currentEvent, data: JSON.parse(raw) };
        } catch {
          // skip malformed
        }
        currentEvent = "";
      }
    }
  }
}

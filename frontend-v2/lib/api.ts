function resolveApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");
  if (!raw) return "/api/v1";
  if (raw.endsWith("/api/v1")) return raw;
  if (raw.endsWith("/api")) return `${raw}/v1`;
  return `${raw}/api/v1`;
}

export function getBackendBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");
  if (!raw || raw.startsWith("/")) return "http://localhost:8000";
  if (raw.endsWith("/api/v1")) return raw.slice(0, -"/api/v1".length);
  if (raw.endsWith("/api")) return raw.slice(0, -"/api".length);
  return raw;
}

const API_BASE_URL = resolveApiBaseUrl();

function normalizeErrors(payload: Record<string, unknown> | null): string[] {
  if (!payload) return [];

  if (Array.isArray(payload.errors) && payload.errors.length) {
    return payload.errors
      .map((e: Record<string, unknown>) => (e?.message || e?.code) as string)
      .filter(Boolean);
  }

  if (Array.isArray(payload.detail)) {
    return payload.detail
      .map((item: Record<string, unknown>) => (item?.msg || item?.message) as string)
      .filter(Boolean);
  }

  if (typeof payload.detail === "string") return [payload.detail];
  if (typeof payload.message === "string") return [payload.message];

  return [];
}

export function formatApiError(
  payload: Record<string, unknown> | null,
  fallback = "Request failed."
): string {
  const messages = normalizeErrors(payload);
  return messages.length ? messages.join(" ") : fallback;
}

async function request<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T | null> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(options.headers as Record<string, string>),
  };

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  const payload = await response.json().catch(() => null);

  if (!response.ok || payload?.success === false) {
    throw new Error(
      formatApiError(payload, `${response.status} ${response.statusText}`)
    );
  }

  return (payload?.data as T) ?? null;
}

// ─── Endpoints ───────────────────────────────────────────────────────────────

export function getHealth() {
  return request<{ status: string; version: string }>("/health");
}

export function createHunt(payload: Record<string, unknown>) {
  return request("/hunts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function recommendCareer(payload: Record<string, unknown>) {
  return request("/recommend-career", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getHunt(huntId: string) {
  return request(`/hunts/${encodeURIComponent(huntId)}`);
}

export function getHuntJobs(huntId: string) {
  return request(`/hunts/${encodeURIComponent(huntId)}/jobs`);
}

export function getHuntApplications(huntId: string) {
  return request(`/hunts/${encodeURIComponent(huntId)}/applications`);
}

export function getAnalytics() {
  return request("/analytics");
}

export function recordIntent(payload: { message: string; session_id: string }, userId: string) {
  return request(`/intelligence/intent?user_id=${encodeURIComponent(userId)}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getCareerDiscovery(
  payload: { skills?: string[]; interests?: string[] },
  userId: string
) {
  return request(`/intelligence/career-discovery?user_id=${encodeURIComponent(userId)}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getBehaviorProfile(userId?: string) {
  const qs = userId ? `?user_id=${encodeURIComponent(userId)}` : "";
  return request(`/behavior-profile${qs}`);
}

export function getStrategy(userId?: string) {
  const qs = userId ? `?user_id=${encodeURIComponent(userId)}` : "";
  return request(`/strategy${qs}`);
}

export function getIntelligenceProfile(userId: string) {
  return request(`/intelligence/profile?user_id=${encodeURIComponent(userId)}`);
}

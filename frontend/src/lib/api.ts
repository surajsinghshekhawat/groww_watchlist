const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

export type HealthResponse = {
  status: string;
  app: string;
  env: string;
  market_data_mode: string;
};

export type TokenBundle = {
  access_token: string;
  token_type: string;
  expires_in_minutes: number;
};

export type AuthResponse = {
  user: {
    user_id: string;
    email: string;
    display_name: string;
    sensitivity?: string;
  };
  token: TokenBundle;
};

export type DigestItem = {
  event_id: string;
  instrument: { instrument_id: string; symbol: string; company_name: string };
  severity: string;
  status: string;
  tier: string;
  attention_score: number;
  significance: number;
  novelty: number;
  confidence: number;
  confidence_breakdown?: string | null;
  explanation: string;
  evidence: Record<string, unknown>;
  peers?: Array<{
    instrument_id: string;
    symbol: string;
    company_name: string;
    return: number;
    vs_stock: number;
  }>;
  retrieval?: Array<{
    source: string;
    title: string;
    origin: string;
    score?: number | null;
  }>;
  user_note?: string | null;
  user_feedback?: "useful" | "noise" | "already_knew" | string | null;
  version: number;
  detected_at: string;
  data_conflict?: boolean;
  data_age_seconds?: number | null;
};

export type IgnoredItem = {
  instrument_id: string;
  symbol: string;
  company_name: string;
  reason: string;
  detail?: string | null;
};

export type DigestResponse = {
  generated_at: string;
  last_checked_at: string | null;
  watchlist_id: string;
  items: DigestItem[];
  ignored?: IgnoredItem[];
  summary: {
    high_attention: number;
    worth_watching: number;
    notable: number;
    hidden_high?: number;
    ignored_count?: number;
    empty_hint?: string | null;
    headline?: string | null;
  };
  market_data_mode: string;
  data_age_seconds?: number | null;
  novelty_scope?: string;
};

export type WatchlistResponse = {
  watchlist_id: string;
  name: string;
  version: number;
  updated_at?: string;
  instruments: Array<{
    instrument_id: string;
    symbol: string;
    company_name: string;
    exchange: string;
    sector: string;
    note?: string | null;
  }>;
};

export type PriceRow = {
  instrument_id: string;
  symbol: string;
  company_name: string;
  sector: string;
  last_price: number | null;
  prev_price: number | null;
  change_pct: number | null;
  volume: number | null;
  as_of: string | null;
  data_age_seconds: number | null;
};

export type NotificationItem = {
  notification_id: string;
  watchlist_id: string | null;
  event_id: string | null;
  title: string;
  body: string;
  severity: string;
  read_at: string | null;
  created_at: string;
};

export type SettingsResponse = {
  sensitivity: string;
  display_name: string;
  email: string;
};

async function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (err) {
    if (err instanceof DOMException && err.name === "TimeoutError") {
      throw new Error(`Request timed out talking to ${API_URL}`);
    }
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error(`Request aborted / timed out talking to ${API_URL}`);
    }
    const msg = err instanceof Error ? err.message : "Network error";
    // Chrome extensions often wrap fetch and break localhost (Failed to fetch)
    throw new Error(
      `${msg}. If this persists, open the app in Incognito (extensions can block API calls). API: ${API_URL}`
    );
  }
}

function authHeaders(token?: string | null): HeadersInit {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function readError(res: Response, fallback: string): Promise<string> {
  const body = await res.json().catch(() => null);
  return body?.error?.message ?? `${fallback} (${res.status})`;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await apiFetch(`${API_URL}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Health check failed (${res.status})`);
  return res.json();
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const res = await apiFetch(`${API_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ email, password }),
    signal: AbortSignal.timeout(20000),
  });
  if (!res.ok) throw new Error(await readError(res, "Login failed"));
  const data = (await res.json()) as AuthResponse;
  if (!data?.token?.access_token) {
    throw new Error("Login response missing access_token");
  }
  return data;
}

export async function register(
  email: string,
  password: string,
  displayName: string
): Promise<AuthResponse> {
  const res = await apiFetch(`${API_URL}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ email, password, display_name: displayName }),
    signal: AbortSignal.timeout(20000),
  });
  if (!res.ok) throw new Error(await readError(res, "Register failed"));
  const data = (await res.json()) as AuthResponse;
  if (!data?.token?.access_token) {
    throw new Error("Register response missing access_token");
  }
  return data;
}

export async function listWatchlists(token: string): Promise<WatchlistResponse[]> {
  const res = await apiFetch(`${API_URL}/api/v1/watchlists`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Watchlists failed (${res.status})`);
  return res.json();
}

export async function createWatchlist(token: string, name: string): Promise<WatchlistResponse> {
  const res = await apiFetch(`${API_URL}/api/v1/watchlists`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(await readError(res, "Create failed"));
  return res.json();
}

export async function renameWatchlist(
  token: string,
  watchlistId: string,
  name: string,
  version: number
): Promise<WatchlistResponse> {
  const res = await apiFetch(`${API_URL}/api/v1/watchlists/${watchlistId}`, {
    method: "PATCH",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ name, version }),
  });
  if (!res.ok) throw new Error(await readError(res, "Rename failed"));
  return res.json();
}

export async function deleteWatchlist(token: string, watchlistId: string): Promise<void> {
  const res = await apiFetch(`${API_URL}/api/v1/watchlists/${watchlistId}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(await readError(res, "Delete failed"));
}

export async function fetchDigest(
  token: string,
  watchlistId: string
): Promise<DigestResponse> {
  const res = await apiFetch(`${API_URL}/api/v1/watchlists/${watchlistId}/digest`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Digest failed (${res.status})`);
  return res.json();
}

export async function fetchPrices(token: string, watchlistId: string): Promise<PriceRow[]> {
  const res = await apiFetch(`${API_URL}/api/v1/watchlists/${watchlistId}/prices`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Prices failed (${res.status})`);
  return res.json();
}

export async function markSeen(
  token: string,
  watchlistId: string,
  items: Array<{ event_id: string; severity_seen: string; event_version: number }>
): Promise<void> {
  const res = await apiFetch(`${API_URL}/api/v1/watchlists/${watchlistId}/mark-seen`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ items }),
  });
  if (!res.ok) throw new Error(`Mark seen failed (${res.status})`);
}

export type FeedbackLabel = "useful" | "noise" | "already_knew";

export async function submitEventFeedback(
  token: string,
  eventId: string,
  label: FeedbackLabel,
  watchlistId?: string
): Promise<{ label: string; cleared_from_digest: boolean }> {
  const res = await apiFetch(`${API_URL}/api/v1/events/${eventId}/feedback`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      label,
      watchlist_id: watchlistId ?? null,
    }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.error?.message || `Feedback failed (${res.status})`);
  }
  return res.json();
}

export async function resetSeen(token: string, watchlistId: string): Promise<void> {
  const res = await apiFetch(`${API_URL}/api/v1/watchlists/${watchlistId}/reset-seen`, {
    method: "POST",
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`Reset seen failed (${res.status})`);
}

export async function searchInstruments(
  token: string,
  q: string
): Promise<
  Array<{
    instrument_id: string;
    symbol: string;
    company_name: string;
    exchange: string;
    sector: string;
    is_index: boolean;
  }>
> {
  const res = await apiFetch(
    `${API_URL}/api/v1/instruments/search?q=${encodeURIComponent(q)}&limit=15`,
    { headers: authHeaders(token), cache: "no-store" }
  );
  if (!res.ok) throw new Error(`Search failed (${res.status})`);
  return res.json();
}

export async function addInstrument(
  token: string,
  watchlistId: string,
  instrumentId: string,
  version: number,
  note?: string
): Promise<WatchlistResponse> {
  const res = await apiFetch(`${API_URL}/api/v1/watchlists/${watchlistId}/instruments`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      instrument_id: instrumentId,
      version,
      note: note || null,
    }),
  });
  if (!res.ok) throw new Error(await readError(res, "Add failed"));
  return res.json();
}

export async function removeInstrument(
  token: string,
  watchlistId: string,
  instrumentId: string,
  version: number
): Promise<WatchlistResponse> {
  const res = await apiFetch(
    `${API_URL}/api/v1/watchlists/${watchlistId}/instruments/${instrumentId}?version=${version}`,
    {
      method: "DELETE",
      headers: authHeaders(token),
    }
  );
  if (!res.ok) throw new Error(await readError(res, "Remove failed"));
  return res.json();
}

export async function fetchNotifications(
  token: string,
  unreadOnly = false
): Promise<NotificationItem[]> {
  const res = await apiFetch(
    `${API_URL}/api/v1/notifications?unread_only=${unreadOnly ? "true" : "false"}`,
    { headers: authHeaders(token), cache: "no-store" }
  );
  if (!res.ok) throw new Error(`Notifications failed (${res.status})`);
  return res.json();
}

export async function markNotificationsRead(token: string): Promise<void> {
  const res = await apiFetch(`${API_URL}/api/v1/notifications/mark-read`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ notification_ids: null }),
  });
  if (!res.ok) throw new Error(await readError(res, "Mark read failed"));
}

export async function touchChecked(token: string, watchlistId: string): Promise<string | null> {
  const res = await apiFetch(`${API_URL}/api/v1/watchlists/${watchlistId}/touch-checked`, {
    method: "POST",
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(await readError(res, "Touch checked failed"));
  const data = (await res.json()) as { last_checked_at?: string };
  return data.last_checked_at ?? null;
}

export async function createWatchlistFromIntent(
  token: string,
  prompt: string
): Promise<{
  watchlist: WatchlistResponse;
  plan: {
    watchlist_name: string;
    symbols_requested: string[];
    sectors_requested: string[];
    themes: string[];
    rationale: string;
    matched_symbols: string[];
    model: string;
  };
}> {
  const res = await apiFetch(`${API_URL}/api/v1/watchlists/from-intent`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
    signal: AbortSignal.timeout(30000),
  });
  if (!res.ok) throw new Error(await readError(res, "Intent watchlist failed"));
  return res.json();
}

export type IntentPreview = {
  proposed_name: string;
  rationale: string;
  model: string;
  symbols_requested: string[];
  sectors_requested: string[];
  themes: string[];
  matches: Array<{
    instrument_id: string;
    symbol: string;
    company_name: string;
    sector: string;
    industry: string;
  }>;
};

export async function previewWatchlistFromIntent(
  token: string,
  prompt: string
): Promise<IntentPreview> {
  const res = await apiFetch(`${API_URL}/api/v1/watchlists/from-intent/preview`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
    signal: AbortSignal.timeout(30000),
  });
  if (!res.ok) throw new Error(await readError(res, "Intent preview failed"));
  return res.json();
}

export async function confirmWatchlistFromIntent(
  token: string,
  payload: {
    name: string;
    instrument_ids: string[];
    note?: string;
    prompt?: string;
  }
): Promise<{ watchlist: WatchlistResponse; matched_symbols: string[] }> {
  const res = await apiFetch(`${API_URL}/api/v1/watchlists/from-intent/confirm`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(20000),
  });
  if (!res.ok) throw new Error(await readError(res, "Create watchlist failed"));
  return res.json();
}

export async function fetchVapidPublicKey(): Promise<{ public_key: string; configured: boolean }> {
  const res = await apiFetch(`${API_URL}/api/v1/push/vapid-public-key`, { cache: "no-store" });
  if (!res.ok) throw new Error(await readError(res, "VAPID key unavailable"));
  const data = (await res.json()) as { public_key?: string; configured?: boolean };
  if (!data.public_key) throw new Error("VAPID public key missing in response");
  return { public_key: data.public_key, configured: Boolean(data.configured) };
}

export async function fetchPushStatus(
  token: string
): Promise<{ configured: boolean; subscribed: boolean; subscription_count: number }> {
  const res = await apiFetch(`${API_URL}/api/v1/push/status`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Push status failed (${res.status})`);
  return res.json();
}

export async function subscribePush(
  token: string,
  subscription: { endpoint: string; keys: { p256dh: string; auth: string } }
): Promise<void> {
  const res = await apiFetch(`${API_URL}/api/v1/push/subscribe`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(subscription),
  });
  if (!res.ok) throw new Error(await readError(res, "Push subscribe failed"));
}

export async function unsubscribePush(token: string, endpoint: string): Promise<void> {
  const res = await apiFetch(`${API_URL}/api/v1/push/unsubscribe`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ endpoint }),
  });
  if (!res.ok) throw new Error(await readError(res, "Push unsubscribe failed"));
}

export async function fetchSettings(token: string): Promise<SettingsResponse> {
  const res = await apiFetch(`${API_URL}/api/v1/me/settings`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Settings failed (${res.status})`);
  return res.json();
}

export async function updateSensitivity(
  token: string,
  sensitivity: string
): Promise<SettingsResponse> {
  const res = await apiFetch(`${API_URL}/api/v1/me/settings`, {
    method: "PATCH",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ sensitivity }),
  });
  if (!res.ok) throw new Error(await readError(res, "Settings update failed"));
  return res.json();
}

export function getApiBaseUrl(): string {
  return API_URL;
}

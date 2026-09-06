"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { AlertsPanel } from "@/components/AlertsPanel";
import { AttentionPanel } from "@/components/AttentionPanel";
import { InfoPanel } from "@/components/InfoPanel";
import { LoginForm } from "@/components/LoginForm";
import { MarketTapePanel } from "@/components/MarketTapePanel";
import { SettingsPanel } from "@/components/SettingsPanel";
import { WatchlistEditor } from "@/components/WatchlistEditor";
import { useWatchlistSync } from "@/hooks/useWatchlistSync";
import {
  createWatchlist,
  fetchDigest,
  listWatchlists,
  markSeen,
  resetSeen,
  submitEventFeedback,
  type DigestItem,
  type DigestResponse,
  type WatchlistResponse,
} from "@/lib/api";

const TOKEN_KEY = "smw_access_token";

type Tab = "market" | "watchlist" | "attention" | "alerts" | "settings" | "info";

const TABS: Array<{ id: Tab; label: string }> = [
  { id: "market", label: "Market" },
  { id: "watchlist", label: "Watchlist" },
  { id: "attention", label: "Attention" },
  { id: "alerts", label: "Alerts" },
  { id: "settings", label: "Settings" },
  { id: "info", label: "Info" },
];

export function WatchlistApp() {
  const [token, setToken] = useState<string | null>(null);
  const [lists, setLists] = useState<WatchlistResponse[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistResponse | null>(null);
  const [digest, setDigest] = useState<DigestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [tab, setTab] = useState<Tab>("attention");
  const watchlistIdRef = useRef<string | null>(null);

  useEffect(() => {
    watchlistIdRef.current = watchlist?.watchlist_id ?? null;
  }, [watchlist?.watchlist_id]);

  useEffect(() => {
    setMounted(true);
    const saved = window.localStorage.getItem(TOKEN_KEY);
    if (saved) setToken(saved);
  }, []);

  const refreshDigest = useCallback(async () => {
    if (!token || !watchlist) return;
    const listId = watchlist.watchlist_id;
    try {
      const dig = await fetchDigest(token, listId);
      if (watchlistIdRef.current !== listId) return;
      setDigest(dig);
      setRefreshKey((k) => k + 1);
      setError(null);
    } catch (err) {
      if (watchlistIdRef.current !== listId) return;
      setError(err instanceof Error ? err.message : "Digest refresh failed");
    }
  }, [token, watchlist]);

  const loadWatchlist = useCallback(async (accessToken: string, preferredId?: string) => {
    setLoading(true);
    setError(null);
    setAuthError(null);
    try {
      let all = await listWatchlists(accessToken);
      if (!all.length) {
        const created = await createWatchlist(accessToken, "My Watchlist");
        all = [created];
      }
      setLists(all);
      const primary =
        all.find((w) => w.watchlist_id === preferredId) ?? all[0];
      watchlistIdRef.current = primary.watchlist_id;
      setWatchlist(primary);
      setLoading(false);

      // Digest (LLM) can take several seconds — never block leaving the login screen
      void (async () => {
        try {
          const dig = await fetchDigest(accessToken, primary.watchlist_id);
          if (watchlistIdRef.current && watchlistIdRef.current !== primary.watchlist_id) {
            return;
          }
          setDigest(dig);
          setRefreshKey((k) => k + 1);
          setError(null);
        } catch (digErr) {
          if (watchlistIdRef.current && watchlistIdRef.current !== primary.watchlist_id) {
            return;
          }
          setError(
            digErr instanceof Error
              ? `Attention digest failed: ${digErr.message}`
              : "Attention digest failed"
          );
        }
      })();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load workspace";
      setError(msg);
      setAuthError(msg);
      window.localStorage.removeItem(TOKEN_KEY);
      setToken(null);
      setWatchlist(null);
      setLists([]);
      setDigest(null);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!mounted || !token) return;
    void loadWatchlist(token);
  }, [mounted, token, loadWatchlist]);

  const { connection } = useWatchlistSync({
    watchlistId: watchlist?.watchlist_id ?? null,
    token,
    onRefresh: refreshDigest,
  });

  function onLoginSuccess(accessToken: string) {
    setAuthError(null);
    setError(null);
    window.localStorage.setItem(TOKEN_KEY, accessToken);
    setToken(accessToken);
  }

  function onLogout() {
    window.localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setWatchlist(null);
    setDigest(null);
    setLists([]);
    setError(null);
    setAuthError(null);
  }

  async function onMarkSeen(item: DigestItem) {
    if (!token || !watchlist) return;
    // Optimistic: remove this instrument from digest immediately
    const instrumentId = item.instrument.instrument_id;
    setDigest((prev) => {
      if (!prev) return prev;
      const remaining = prev.items.filter((i) => i.instrument.instrument_id !== instrumentId);
      const ignored = [
        ...(prev.ignored ?? []),
        {
          instrument_id: instrumentId,
          symbol: item.instrument.symbol,
          company_name: item.instrument.company_name,
          reason: "already_seen",
          detail: "You already marked this event state as seen.",
        },
      ];
      return {
        ...prev,
        items: remaining,
        ignored,
        summary: {
          high_attention: remaining.filter((i) => i.tier === "HIGH_ATTENTION").length,
          worth_watching: remaining.filter((i) => i.tier === "WORTH_WATCHING").length,
          notable: remaining.filter((i) => i.tier === "NOTABLE").length,
          hidden_high: prev.summary.hidden_high ?? 0,
          ignored_count: ignored.length,
          empty_hint: prev.summary.empty_hint,
          headline:
            remaining.length === 0
              ? `Today: nothing novel enough for the digest — ${ignored.length} name(s) explained under What we ignored.`
              : prev.summary.headline,
        },
      };
    });
    try {
      await markSeen(token, watchlist.watchlist_id, [
        {
          event_id: item.event_id,
          severity_seen: item.severity,
          event_version: item.version,
        },
      ]);
      setRefreshKey((k) => k + 1);
      await refreshDigest();
    } catch (err) {
      await refreshDigest();
      window.alert(
        err instanceof Error
          ? err.message
          : "Mark seen failed — try disabling browser extensions on localhost."
      );
    }
  }

  async function onFeedback(item: DigestItem, label: "useful" | "noise" | "already_knew") {
    if (!token || !watchlist) return;
    if (label === "noise" || label === "already_knew") {
      const instrumentId = item.instrument.instrument_id;
      setDigest((prev) => {
        if (!prev) return prev;
        const remaining = prev.items.filter((i) => i.instrument.instrument_id !== instrumentId);
        const ignored = [
          ...(prev.ignored ?? []),
          {
            instrument_id: instrumentId,
            symbol: item.instrument.symbol,
            company_name: item.instrument.company_name,
            reason: label === "noise" ? "feedback_noise" : "feedback_already_knew",
            detail:
              label === "noise"
                ? "You labeled this as noise."
                : "You already knew about this — cleared from Attention.",
          },
        ];
        return {
          ...prev,
          items: remaining,
          ignored,
          summary: {
            high_attention: remaining.filter((i) => i.tier === "HIGH_ATTENTION").length,
            worth_watching: remaining.filter((i) => i.tier === "WORTH_WATCHING").length,
            notable: remaining.filter((i) => i.tier === "NOTABLE").length,
            hidden_high: prev.summary.hidden_high ?? 0,
            ignored_count: ignored.length,
            empty_hint: prev.summary.empty_hint,
            headline:
              remaining.length === 0
                ? `Today: nothing novel enough for the digest — ${ignored.length} name(s) explained under What we ignored.`
                : prev.summary.headline,
          },
        };
      });
    } else {
      setDigest((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          items: prev.items.map((i) =>
            i.event_id === item.event_id ? { ...i, user_feedback: label } : i
          ),
        };
      });
    }
    try {
      await submitEventFeedback(token, item.event_id, label, watchlist.watchlist_id);
      setRefreshKey((k) => k + 1);
      if (label !== "useful") await refreshDigest();
    } catch (err) {
      await refreshDigest();
      window.alert(err instanceof Error ? err.message : "Feedback failed");
    }
  }

  async function onResetDemo() {
    if (!token || !watchlist) return;
    try {
      await resetSeen(token, watchlist.watchlist_id);
      await refreshDigest();
    } catch (err) {
      window.alert(
        err instanceof Error
          ? err.message
          : "Reset failed — try Incognito (extensions break fetch)."
      );
    }
  }

  async function onWatchlistChanged(next: WatchlistResponse) {
    setWatchlist(next);
    setLists((prev) => prev.map((l) => (l.watchlist_id === next.watchlist_id ? next : l)));
    if (!token) return;
    try {
      const all = await listWatchlists(token);
      setLists(all);
      const fresh = all.find((w) => w.watchlist_id === next.watchlist_id) ?? next;
      setWatchlist(fresh);
      const dig = await fetchDigest(token, fresh.watchlist_id);
      setDigest(dig);
      setRefreshKey((k) => k + 1);
    } catch {
      try {
        const dig = await fetchDigest(token, next.watchlist_id);
        setDigest(dig);
      } catch {
        /* keep prior digest */
      }
    }
  }

  if (!mounted) {
    return <p className="text-sm text-[var(--muted)]">Loading…</p>;
  }

  if (!token) {
    return <LoginForm onSuccess={onLoginSuccess} bootstrapError={authError} />;
  }

  if (loading && !watchlist) {
    return (
      <div className="space-y-2 text-sm text-[var(--muted)]">
        <p>Signing you in…</p>
        <p className="text-xs">Loading watchlist (Attention digest may take a few seconds).</p>
      </div>
    );
  }

  if (!watchlist) {
    return (
      <div className="rounded-lg border border-signal-high/40 bg-signal-high/10 p-4 text-sm text-signal-high">
        {error ?? "Could not open a watchlist."}
        <button type="button" className="ml-3 underline" onClick={onLogout}>
          Sign in again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error ? (
        <div className="rounded-lg border border-signal-notable/40 bg-signal-notable/10 px-3 py-2 text-xs text-signal-notable">
          {error}
          <button
            type="button"
            className="ml-2 underline"
            onClick={() => {
              setError(null);
              void refreshDigest();
            }}
          >
            Retry digest
          </button>
        </div>
      ) : null}

      <nav className="flex flex-wrap gap-1 rounded-xl border border-[var(--line)] bg-ink-900/50 p-1">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`rounded-lg px-4 py-2 text-sm transition ${
              tab === t.id
                ? "bg-mint-500/20 text-mint-400"
                : "text-[var(--muted)] hover:text-white"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "market" ? <MarketTapePanel /> : null}

      {tab === "watchlist" ? (
        <WatchlistEditor
          token={token}
          watchlist={watchlist}
          lists={lists}
          onChanged={(next) => void onWatchlistChanged(next)}
          onSelectWatchlist={(id) => void loadWatchlist(token, id)}
          onWatchlistCreated={(created) => {
            setLists((prev) => {
              if (prev.some((l) => l.watchlist_id === created.watchlist_id)) return prev;
              return [created, ...prev];
            });
            setWatchlist(created);
            setTab("attention");
            void loadWatchlist(token, created.watchlist_id);
          }}
        />
      ) : null}

      {tab === "attention" ? (
        <AttentionPanel
          token={token}
          watchlist={watchlist}
          digest={digest}
          connection={connection}
          onMarkSeen={onMarkSeen}
          onFeedback={onFeedback}
          onResetDemo={onResetDemo}
          refreshKey={refreshKey}
          onTouched={(iso) => {
            setDigest((prev) => (prev ? { ...prev, last_checked_at: iso } : prev));
            setRefreshKey((k) => k + 1);
          }}
        />
      ) : null}

      {tab === "alerts" ? <AlertsPanel token={token} refreshKey={refreshKey} /> : null}

      {tab === "settings" ? (
        <SettingsPanel
          token={token}
          lists={lists}
          activeId={watchlist.watchlist_id}
          onSelect={(id) => void loadWatchlist(token, id)}
          onListsChanged={setLists}
          onSensitivityChanged={() => void refreshDigest()}
          onLogout={onLogout}
        />
      ) : null}

      {tab === "info" ? <InfoPanel /> : null}
    </div>
  );
}

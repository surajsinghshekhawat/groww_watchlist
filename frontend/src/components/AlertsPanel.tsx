"use client";

import { useEffect, useState } from "react";

import {
  fetchNotifications,
  markNotificationsRead,
  type NotificationItem,
} from "@/lib/api";

export function AlertsPanel({ token, refreshKey }: { token: string; refreshKey?: number }) {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void fetchNotifications(token, true)
      .then((rows) => {
        if (!cancelled) {
          setItems(rows);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setItems([]);
          setError(err instanceof Error ? err.message : "Failed to load alerts");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token, refreshKey]);

  async function markAll() {
    setBusy(true);
    setError(null);
    try {
      await markNotificationsRead(token);
      setItems([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Mark all read failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-3xl text-white">Alerts</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Unread, sensitivity-gated alerts from the background engine. Mark seen on
            Attention also clears the matching alert.
          </p>
        </div>
        <button
          type="button"
          disabled={busy || items.length === 0}
          onClick={() => void markAll()}
          className="rounded-md border border-[var(--line)] px-3 py-1.5 text-xs text-white disabled:opacity-50"
        >
          {busy ? "Marking…" : "Mark all read"}
        </button>
      </div>
      {error ? <p className="text-xs text-signal-high">{error}</p> : null}
      {items.length === 0 ? (
        <p className="rounded-xl border border-[var(--line)] bg-ink-900/40 p-6 text-sm text-[var(--muted)]">
          No unread alerts. New HIGH (or above your sensitivity) events appear here in
          near real-time via live-sim + WebSocket / polling.
        </p>
      ) : (
        <ul className="space-y-3">
          {items.map((n) => (
            <li
              key={n.notification_id}
              className="rounded-xl border border-mint-500/30 bg-mint-500/5 p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-white">{n.title}</p>
                  <p className="mt-1 text-xs text-[var(--muted)]">{n.body}</p>
                  <p className="mt-2 text-[10px] text-[var(--muted)]">
                    {new Date(n.created_at).toLocaleString("en-IN", {
                      timeZone: "Asia/Kolkata",
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                  </p>
                </div>
                <span className="text-[10px] uppercase text-[var(--muted)]">{n.severity}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";

import {
  fetchNotifications,
  markNotificationsRead,
  type NotificationItem,
} from "@/lib/api";

export function NotificationBell({
  token,
  refreshKey,
}: {
  token: string;
  refreshKey?: number;
}) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const rows = await fetchNotifications(token, true);
      setItems(rows);
      setError(null);
    } catch (err) {
      setItems([]);
      setError(err instanceof Error ? err.message : "Failed to load");
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  const unread = items.length;

  async function onMarkAll() {
    try {
      await markNotificationsRead(token);
      setItems([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Mark read failed");
    }
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="rounded-md border border-[var(--line)] px-3 py-1.5 text-xs text-white"
      >
        Alerts{unread > 0 ? ` (${unread})` : ""}
      </button>
      {open ? (
        <div className="absolute right-0 z-20 mt-2 w-80 rounded-lg border border-[var(--line)] bg-ink-950 p-3 shadow-xl">
          <div className="mb-2 flex items-center justify-between gap-2">
            <p className="text-xs font-semibold text-white">Unread alerts</p>
            {unread > 0 ? (
              <button
                type="button"
                className="text-[10px] text-mint-400 underline"
                onClick={() => void onMarkAll()}
              >
                Mark all read
              </button>
            ) : null}
          </div>
          {error ? <p className="text-[11px] text-signal-high">{error}</p> : null}
          {items.length === 0 ? (
            <p className="text-xs text-[var(--muted)]">No unread alerts.</p>
          ) : (
            <ul className="max-h-64 space-y-2 overflow-auto">
              {items.map((n) => (
                <li key={n.notification_id} className="rounded-md border border-[var(--line)] p-2">
                  <p className="text-xs text-white">{n.title}</p>
                  <p className="mt-1 text-[11px] text-[var(--muted)]">{n.body}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}

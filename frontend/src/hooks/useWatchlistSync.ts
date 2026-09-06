"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { getApiBaseUrl } from "@/lib/api";

type ConnectionState = "connecting" | "live" | "polling" | "offline";

/**
 * WebSocket with automatic fallback to digest polling when WS fails.
 */
export function useWatchlistSync(opts: {
  watchlistId: string | null;
  token: string | null;
  onRefresh: () => Promise<void>;
  activePollMs?: number;
  backgroundPollMs?: number;
}) {
  const {
    watchlistId,
    token,
    onRefresh,
    activePollMs = 8000,
    backgroundPollMs = 60000,
  } = opts;

  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const wsRef = useRef<WebSocket | null>(null);

  const refresh = useCallback(async () => {
    try {
      await onRefresh();
    } catch {
      // swallow — UI shows last good state
    }
  }, [onRefresh]);

  useEffect(() => {
    if (!watchlistId || !token) return;

    let cancelled = false;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    let usePolling = false;

    const startPolling = (ms: number) => {
      usePolling = true;
      setConnection("polling");
      if (pollTimer) clearInterval(pollTimer);
      pollTimer = setInterval(() => {
        void refresh();
      }, ms);
    };

    const wsBase = getApiBaseUrl().replace(/^http/, "ws");
    const url = `${wsBase}/ws/watchlists/${watchlistId}?token=${encodeURIComponent(token)}`;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (cancelled) return;
        setConnection("live");
        if (pollTimer) {
          clearInterval(pollTimer);
          pollTimer = null;
        }
        usePolling = false;
      };

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data as string) as { type?: string };
          if (msg.type === "event" || msg.type === "heartbeat") {
            void refresh();
          }
          if (msg.type === "degraded") {
            startPolling(activePollMs);
          }
        } catch {
          // ignore malformed
        }
      };

      ws.onerror = () => {
        if (!cancelled) startPolling(activePollMs);
      };

      ws.onclose = () => {
        if (!cancelled && !usePolling) startPolling(activePollMs);
      };
    } catch {
      startPolling(activePollMs);
    }

    const onVisibility = () => {
      if (document.hidden) {
        if (usePolling) startPolling(backgroundPollMs);
      } else if (usePolling) {
        startPolling(activePollMs);
        void refresh();
      }
    };
    document.addEventListener("visibilitychange", onVisibility);

    // Always keep a slow safety poll even when live
    const safety = setInterval(() => {
      if (!cancelled) void refresh();
    }, backgroundPollMs);

    return () => {
      cancelled = true;
      document.removeEventListener("visibilitychange", onVisibility);
      if (pollTimer) clearInterval(pollTimer);
      clearInterval(safety);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [watchlistId, token, refresh, activePollMs, backgroundPollMs]);

  return { connection };
}

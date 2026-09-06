"use client";

import { useEffect, useState } from "react";

import { fetchHealth, type HealthResponse } from "@/lib/api";

type Status = "loading" | "ok" | "error";

export function ApiStatus() {
  const [status, setStatus] = useState<Status>("loading");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await fetchHealth();
        if (cancelled) return;
        setHealth(data);
        setStatus("ok");
      } catch (err) {
        if (cancelled) return;
        setStatus("error");
        setError(err instanceof Error ? err.message : "Could not reach API");
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (status === "loading") {
    return (
      <span className="rounded-md bg-ink-800 px-3 py-1.5 text-xs text-[var(--muted)]">
        Checking API…
      </span>
    );
  }

  if (status === "error") {
    return (
      <span
        className="rounded-md bg-signal-high/15 px-3 py-1.5 text-xs text-signal-high"
        role="status"
      >
        API unavailable{error ? ` — ${error}` : ""}
      </span>
    );
  }

  return (
    <span
      className="rounded-md bg-mint-500/15 px-3 py-1.5 text-xs text-mint-400"
      role="status"
    >
      Connected · {health?.market_data_mode ?? "unknown"} mode
    </span>
  );
}

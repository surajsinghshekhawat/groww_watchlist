"use client";

/**
 * Age of last ingested price tick (wall-clock).
 * Replay mode: informational only — not a live outage.
 */
export function StaleDataBadge({
  ageSeconds,
  mode = "replay",
}: {
  ageSeconds: number | null;
  mode?: string;
}) {
  if (ageSeconds == null) return null;
  if (ageSeconds < 15) return null;

  const mins = Math.max(1, Math.round(ageSeconds / 60));
  const m = mode.toLowerCase();
  const isReplay = m === "replay" || m === "mock" || m.includes("live-sim");

  if (isReplay) {
    return (
      <span
        className="rounded-md bg-signal-watch/15 px-2 py-1 text-xs text-signal-watch"
        role="status"
      >
        Replay snapshot · loaded {mins}m ago
      </span>
    );
  }

  if (ageSeconds > 300) {
    return (
      <span
        className="rounded-md bg-signal-high/15 px-2 py-1 text-xs text-signal-high"
        role="status"
      >
        Stale live data · last tick {mins}m ago (confidence reduced)
      </span>
    );
  }

  return (
    <span
      className="rounded-md bg-signal-watch/15 px-2 py-1 text-xs text-signal-watch"
      role="status"
    >
      Live data delayed {Math.round(ageSeconds)}s
    </span>
  );
}

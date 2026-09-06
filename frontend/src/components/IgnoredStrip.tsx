"use client";

import type { IgnoredItem } from "@/lib/api";

const REASON_LABEL: Record<string, string> = {
  low_significance: "Low significance",
  market_aligned: "Market-aligned",
  already_seen: "Already seen",
  below_sensitivity: "Below sensitivity",
  zero_attention: "Zero attention",
  no_event: "No open event",
  insufficient_history: "Insufficient history",
  index_context_only: "Index (context only)",
};

export function IgnoredStrip({ items }: { items: IgnoredItem[] }) {
  if (!items.length) return null;
  return (
    <section className="rounded-xl border border-[var(--line)] bg-ink-900/30 p-5">
      <h3 className="text-sm font-semibold text-white">What we ignored — and why</h3>
      <p className="mt-1 text-xs text-[var(--muted)]">
        Attention is scarce. These watchlist names did not make the digest.
      </p>
      <ul className="mt-4 space-y-2">
        {items.map((row) => (
          <li
            key={`${row.instrument_id}-${row.reason}`}
            className="rounded-lg border border-[var(--line)] px-3 py-2 text-xs"
          >
            <span className="font-medium text-white">{row.symbol}</span>
            <span className="ml-2 text-signal-watch">
              {REASON_LABEL[row.reason] ?? row.reason}
            </span>
            {row.detail ? (
              <p className="mt-1 text-[var(--muted)]">{row.detail}</p>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

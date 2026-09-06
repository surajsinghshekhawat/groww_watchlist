"use client";

import { useEffect, useState } from "react";

import { fetchPrices, type PriceRow } from "@/lib/api";

export function WatchlistPrices({
  token,
  watchlistId,
  refreshKey,
}: {
  token: string;
  watchlistId: string;
  refreshKey?: number;
}) {
  const [rows, setRows] = useState<PriceRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void fetchPrices(token, watchlistId)
      .then((data) => {
        if (cancelled) return;
        setRows(data);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setRows([]);
        setError(err instanceof Error ? err.message : "Failed to load prices");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, watchlistId, refreshKey]);

  if (loading) {
    return <p className="text-xs text-[var(--muted)]">Loading prices…</p>;
  }

  if (error) {
    return <p className="text-xs text-signal-high">{error}</p>;
  }

  if (rows.length === 0) {
    return (
      <p className="text-xs text-[var(--muted)]">
        No instruments on this watchlist — add names in the Watchlist tab, or sign in as
        demo@example.com and run <code className="text-mint-400">python -m app.demo_pipeline</code>.
      </p>
    );
  }

  const anyPrice = rows.some((r) => r.last_price != null);
  if (!anyPrice) {
    return (
      <p className="text-xs text-[var(--muted)]">
        Watchlist loaded but no PricePoints yet — run{" "}
        <code className="text-mint-400">python -m app.demo_pipeline</code> (API will also ingest
        live-sim ticks every ~8s). When <code className="text-mint-400">MARKET_DATA_MODE=yahoo</code>,
        rows use delayed Yahoo NSE closes instead.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-[10px] text-[var(--muted)]">
        Engine input quotes. <span className="text-white">Change</span> = vs recent session open
        (not the Attention card’s “since last check” return).{" "}
        <span className="text-white">Age</span> = seconds since last ingest (freshness).
      </p>
      <div className="overflow-x-auto rounded-xl border border-[var(--line)]">
        <table className="min-w-full text-left text-xs">
          <thead className="bg-ink-900/80 text-[var(--muted)]">
            <tr>
              <th className="px-3 py-2 font-medium">Symbol</th>
              <th className="px-3 py-2 font-medium">Last</th>
              <th className="px-3 py-2 font-medium">Change (session)</th>
              <th className="px-3 py-2 font-medium">Sector</th>
              <th className="px-3 py-2 font-medium">Age</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.instrument_id} className="border-t border-[var(--line)]">
                <td className="px-3 py-2 text-white">
                  {r.symbol}
                  <span className="ml-2 text-[var(--muted)]">{r.company_name}</span>
                </td>
                <td className="px-3 py-2 text-white">
                  {r.last_price != null ? r.last_price.toFixed(2) : "—"}
                </td>
                <td
                  className={`px-3 py-2 ${
                    (r.change_pct ?? 0) >= 0 ? "text-mint-400" : "text-signal-high"
                  }`}
                >
                  {r.change_pct != null ? `${r.change_pct.toFixed(2)}%` : "—"}
                </td>
                <td className="px-3 py-2 text-[var(--muted)]">{r.sector}</td>
                <td className="px-3 py-2 text-[var(--muted)]" title="Seconds since last price ingest">
                  {r.data_age_seconds != null ? `${Math.round(r.data_age_seconds)}s` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";

import { getApiBaseUrl } from "@/lib/api";

export type TapeQuote = {
  instrument_id: string;
  symbol: string;
  price: number;
  change_pct: number;
  volume: number;
  direction: "up" | "down" | "flat" | string;
  updated_at: string;
  is_index?: boolean;
};

export function MarketTapePanel() {
  const [quotes, setQuotes] = useState<TapeQuote[]>([]);
  const [connected, setConnected] = useState(false);
  const [tapeMode, setTapeMode] = useState("live-sim");
  const [tapeLabel, setTapeLabel] = useState("");
  const [flash, setFlash] = useState<Record<string, string>>({});
  const prev = useRef<Record<string, number>>({});

  useEffect(() => {
    let ws: WebSocket | null = null;
    let poll: ReturnType<typeof setInterval> | null = null;
    let cancelled = false;
    const modeRef = { current: "live-sim" };

    function applyQuotes(next: TapeQuote[]) {
      const flashes: Record<string, string> = {};
      for (const q of next) {
        const before = prev.current[q.symbol];
        if (before != null && q.price !== before) {
          flashes[q.symbol] = q.price > before ? "up" : "down";
        }
        prev.current[q.symbol] = q.price;
      }
      setFlash(flashes);
      setQuotes(next);
      window.setTimeout(() => setFlash({}), 400);
    }

    async function loadOnce() {
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/v1/market/tape`, { cache: "no-store" });
        if (!res.ok) return;
        const body = await res.json();
        if (typeof body.mode === "string") {
          modeRef.current = body.mode;
          setTapeMode(body.mode);
        }
        if (typeof body.label === "string") setTapeLabel(body.label);
        applyQuotes(body.quotes as TapeQuote[]);
      } catch {
        /* ignore */
      }
    }

    void loadOnce();
    poll = setInterval(() => void loadOnce(), 20000);

    try {
      const url = getApiBaseUrl().replace(/^http/, "ws") + "/ws/tape";
      ws = new WebSocket(url);
      ws.onopen = () => {
        if (!cancelled) setConnected(true);
      };
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data as string);
          if (msg.type === "tape" && Array.isArray(msg.quotes)) {
            if (modeRef.current === "yahoo" || modeRef.current === "yfinance") return;
            applyQuotes(msg.quotes);
          }
        } catch {
          /* ignore */
        }
      };
      ws.onclose = () => setConnected(false);
      ws.onerror = () => setConnected(false);
    } catch {
      /* polling already running */
    }

    return () => {
      cancelled = true;
      ws?.close();
      if (poll) clearInterval(poll);
    };
  }, []);

  const equities = quotes.filter((q) => !q.is_index);
  const indices = quotes.filter((q) => q.is_index);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-3xl text-white">Market tape</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            {tapeLabel ||
              (tapeMode === "yahoo"
                ? "Delayed Yahoo Finance NSE quotes — feeds Attention. Not a licensed exchange feed."
                : "Live-sim board — same ticks feed Attention. Not a licensed exchange feed.")}
          </p>
        </div>
        <span className="rounded-md border border-[var(--line)] px-2 py-1 text-xs text-[var(--muted)]">
          {tapeMode === "yahoo" || tapeMode === "yfinance"
            ? "Polling · Yahoo delayed"
            : connected
              ? "Streaming · live-sim"
              : "Polling · live-sim"}
        </span>
      </div>

      {indices.length > 0 ? (
        <div className="grid gap-2 sm:grid-cols-2">
          {indices.map((q) => (
            <QuoteRow key={q.symbol} q={q} flash={flash[q.symbol]} large />
          ))}
        </div>
      ) : null}

      <div className="overflow-hidden rounded-xl border border-[var(--line)]">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-ink-900/70 text-xs uppercase tracking-wide text-[var(--muted)]">
            <tr>
              <th className="px-4 py-3 font-medium">Symbol</th>
              <th className="px-4 py-3 font-medium">LTP</th>
              <th className="px-4 py-3 font-medium">Day %</th>
              <th className="px-4 py-3 font-medium">Volume</th>
            </tr>
          </thead>
          <tbody>
            {equities.map((q) => (
              <tr
                key={q.symbol}
                className={`border-t border-[var(--line)] transition-colors ${
                  flash[q.symbol] === "up"
                    ? "bg-mint-500/10"
                    : flash[q.symbol] === "down"
                      ? "bg-signal-high/10"
                      : ""
                }`}
              >
                <td className="px-4 py-3 font-medium text-white">{q.symbol}</td>
                <td
                  className={`px-4 py-3 tabular-nums ${
                    q.direction === "up"
                      ? "text-mint-400"
                      : q.direction === "down"
                        ? "text-signal-high"
                        : "text-white"
                  }`}
                >
                  {q.price.toFixed(2)}
                </td>
                <td
                  className={`px-4 py-3 tabular-nums ${
                    q.change_pct >= 0 ? "text-mint-400" : "text-signal-high"
                  }`}
                >
                  {q.change_pct >= 0 ? "+" : ""}
                  {q.change_pct.toFixed(2)}%
                </td>
                <td className="px-4 py-3 tabular-nums text-[var(--muted)]">
                  {Math.round(q.volume).toLocaleString("en-IN")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function QuoteRow({
  q,
  flash,
  large,
}: {
  q: TapeQuote;
  flash?: string;
  large?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border border-[var(--line)] bg-ink-900/40 px-4 py-3 ${
        flash === "up" ? "bg-mint-500/10" : flash === "down" ? "bg-signal-high/10" : ""
      }`}
    >
      <p className="text-xs text-[var(--muted)]">{q.symbol}</p>
      <p className={`tabular-nums text-white ${large ? "text-2xl" : "text-lg"}`}>
        {q.price.toFixed(2)}
        <span
          className={`ml-3 text-sm ${q.change_pct >= 0 ? "text-mint-400" : "text-signal-high"}`}
        >
          {q.change_pct >= 0 ? "+" : ""}
          {q.change_pct.toFixed(2)}%
        </span>
      </p>
    </div>
  );
}

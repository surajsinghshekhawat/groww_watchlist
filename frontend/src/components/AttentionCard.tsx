"use client";

import { useMemo, useState } from "react";

import { DataConflictBadge } from "@/components/DataConflictBadge";
import type { DigestItem } from "@/lib/api";

const TIER_LABEL: Record<string, string> = {
  HIGH_ATTENTION: "High attention",
  WORTH_WATCHING: "Worth watching",
  NOTABLE: "Notable",
  LOW: "Low",
};

const TIER_COLOR: Record<string, string> = {
  HIGH_ATTENTION: "text-signal-high border-signal-high/40",
  WORTH_WATCHING: "text-signal-watch border-signal-watch/40",
  NOTABLE: "text-signal-notable border-signal-notable/40",
  LOW: "text-signal-calm border-signal-calm/40",
};

export function AttentionCard({
  item,
  onMarkSeen,
  onFeedback,
}: {
  item: DigestItem;
  onMarkSeen: (item: DigestItem) => Promise<void>;
  onFeedback?: (item: DigestItem, label: "useful" | "noise" | "already_knew") => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [fbBusy, setFbBusy] = useState<string | null>(null);
  const [localFb, setLocalFb] = useState<string | null>(item.user_feedback ?? null);
  const evidence = item.evidence as {
    market_evidence?: { rvol_score?: number; price_anomaly_score?: number };
    context_evidence?: {
      market_return?: number;
      sector_return?: number;
      stock_return?: number;
      market_residual?: number;
      sector_residual?: number;
    };
    information_evidence?: { filing_present?: boolean; filing_id?: string | null };
    persistence_evidence?: { cusum_flag?: boolean };
  };

  const tierClass = TIER_COLOR[item.tier] ?? TIER_COLOR.LOW;
  const feedback = localFb ?? item.user_feedback ?? null;


  const contextLine = useMemo(() => {
    const c = evidence.context_evidence;
    if (!c) return null;
    const stock = c.stock_return != null ? `${(c.stock_return * 100).toFixed(1)}%` : "n/a";
    const market = c.market_return != null ? `${(c.market_return * 100).toFixed(1)}%` : "n/a";
    const sector = c.sector_return != null ? `${(c.sector_return * 100).toFixed(1)}%` : "n/a";
    return `Stock ${stock} · Market ${market} · Sector ${sector}`;
  }, [evidence.context_evidence]);

  return (
    <article className={`rounded-xl border bg-ink-900/50 p-5 ${tierClass}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em]">
            {TIER_LABEL[item.tier] ?? item.tier}
          </p>
          <h3 className="mt-1 font-display text-3xl text-white">
            {item.instrument.company_name}
          </h3>
          <p className="text-sm text-[var(--muted)]">{item.instrument.symbol}</p>
        </div>
        <div className="text-right text-xs text-[var(--muted)]">
          <p>Attention {item.attention_score.toFixed(2)}</p>
          <p>
            S {item.significance.toFixed(2)} · N {item.novelty.toFixed(2)} · C{" "}
            {item.confidence.toFixed(2)}
          </p>
          {item.confidence_breakdown ? (
            <p className="mt-1 max-w-[14rem] text-left text-[10px] leading-snug text-[var(--muted)] sm:ml-auto sm:text-right">
              {item.confidence_breakdown}
            </p>
          ) : null}
        </div>
      </div>

      <p className="mt-4 text-sm leading-relaxed text-[#d7e0ef]">{item.explanation}</p>
      {item.user_note ? (
        <p className="mt-2 text-xs text-mint-400/90">Your note: {item.user_note}</p>
      ) : null}
      {contextLine ? (
        <p className="mt-2 text-xs text-[var(--muted)]">{contextLine}</p>
      ) : null}

      {(item.retrieval?.length ?? 0) > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {item.retrieval!.map((r, idx) => (
            <span
              key={`${r.origin}-${r.source}-${idx}`}
              className="rounded-md border border-mint-500/30 bg-mint-500/10 px-2 py-1 text-[10px] uppercase tracking-wide text-mint-400"
              title={r.source}
            >
              Retrieved · {r.origin}: {r.title.slice(0, 42)}
              {r.title.length > 42 ? "…" : ""}
            </span>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-[10px] uppercase tracking-wide text-[var(--muted)]">
          Retrieved · none
        </p>
      )}

      <div className="mt-3">
        <DataConflictBadge active={Boolean(item.data_conflict)} />
      </div>

      {(item.peers?.length ?? 0) > 0 ? (
        <div className="mt-3 rounded-lg border border-[var(--line)] bg-ink-950/40 p-3 text-xs text-[var(--muted)]">
          <p className="font-semibold text-white">Sector peers</p>
          <ul className="mt-2 space-y-1">
            {item.peers!.map((p) => (
              <li key={p.instrument_id}>
                {p.symbol}: {(p.return * 100).toFixed(1)}%
                <span className="ml-2">
                  (vs this name {(p.vs_stock * 100).toFixed(1)} pp)
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded-md border border-[var(--line)] px-3 py-1.5 text-xs text-white hover:bg-ink-800"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
        >
          {open ? "Hide evidence" : "View evidence"}
        </button>
        <button
          type="button"
          className="rounded-md bg-mint-500/20 px-3 py-1.5 text-xs text-mint-400 hover:bg-mint-500/30 disabled:opacity-50"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await onMarkSeen(item);
            } finally {
              setBusy(false);
            }
          }}
        >
          Mark seen
        </button>
      </div>

      {onFeedback ? (
        <div className="mt-3 rounded-lg border border-[var(--line)] bg-ink-950/40 p-3">
          <p className="text-[10px] uppercase tracking-wide text-[var(--muted)]">
            Was this useful?
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {(
              [
                ["useful", "Useful"],
                ["noise", "Noise"],
                ["already_knew", "Already knew"],
              ] as const
            ).map(([value, label]) => {
              const active = feedback === value;
              return (
                <button
                  key={value}
                  type="button"
                  disabled={fbBusy != null}
                  className={`rounded-md border px-2.5 py-1 text-xs disabled:opacity-50 ${
                    active
                      ? "border-mint-500/50 bg-mint-500/20 text-mint-400"
                      : "border-[var(--line)] text-[var(--muted)] hover:bg-ink-800 hover:text-white"
                  }`}
                  onClick={async () => {
                    setFbBusy(value);
                    try {
                      await onFeedback(item, value);
                      setLocalFb(value);
                    } finally {
                      setFbBusy(null);
                    }
                  }}
                >
                  {fbBusy === value ? "…" : label}
                </button>
              );
            })}
          </div>
          {feedback ? (
            <p className="mt-2 text-[10px] text-[var(--muted)]">
              Saved as <span className="text-mint-400">{feedback.replace("_", " ")}</span>
              {feedback !== "useful" ? " · cleared from Attention" : ""}
            </p>
          ) : (
            <p className="mt-2 text-[10px] text-[var(--muted)]">
              Labels train thresholds later — no public “meaningful” dataset exists.
            </p>
          )}
        </div>
      ) : null}

      {open ? (
        <div className="mt-4 grid gap-2 rounded-lg border border-[var(--line)] bg-ink-950/60 p-4 text-xs text-[var(--muted)] sm:grid-cols-2">
          <p>
            Price anomaly z:{" "}
            {evidence.market_evidence?.price_anomaly_score?.toFixed?.(2) ?? "n/a"}
          </p>
          <p>RVOL: {evidence.market_evidence?.rvol_score?.toFixed?.(2) ?? "n/a"}×</p>
          <p>
            Market residual:{" "}
            {evidence.context_evidence?.market_residual?.toFixed?.(4) ?? "n/a"}
          </p>
          <p>
            Sector residual:{" "}
            {evidence.context_evidence?.sector_residual?.toFixed?.(4) ?? "n/a"}
          </p>
          <p>CUSUM: {evidence.persistence_evidence?.cusum_flag ? "flagged" : "no"}</p>
          <p>
            Filing:{" "}
            {evidence.information_evidence?.filing_present
              ? evidence.information_evidence.filing_id ?? "yes"
              : "none"}
          </p>
        </div>
      ) : null}
    </article>
  );
}

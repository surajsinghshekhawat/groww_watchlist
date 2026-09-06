"use client";

import { useEffect, useState } from "react";

import { AttentionCard } from "@/components/AttentionCard";
import { IgnoredStrip } from "@/components/IgnoredStrip";
import { StaleDataBadge } from "@/components/StaleDataBadge";
import { WatchlistPrices } from "@/components/WatchlistPrices";
import {
  touchChecked,
  type DigestItem,
  type DigestResponse,
  type WatchlistResponse,
} from "@/lib/api";

function formatIst(iso: string): string {
  try {
    return new Intl.DateTimeFormat("en-IN", {
      timeZone: "Asia/Kolkata",
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function AttentionPanel({
  token,
  watchlist,
  digest,
  connection,
  onMarkSeen,
  onFeedback,
  onResetDemo,
  refreshKey,
  onTouched,
}: {
  token: string;
  watchlist: WatchlistResponse;
  digest: DigestResponse | null;
  connection: string;
  onMarkSeen: (item: DigestItem) => Promise<void>;
  onFeedback?: (item: DigestItem, label: "useful" | "noise" | "already_knew") => Promise<void>;
  onResetDemo: () => Promise<void>;
  refreshKey?: number;
  onTouched?: (lastCheckedAt: string) => void;
}) {
  const [localChecked, setLocalChecked] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void touchChecked(token, watchlist.watchlist_id)
      .then((iso) => {
        if (cancelled || !iso) return;
        setLocalChecked(iso);
        onTouched?.(iso);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
    // Touch once when Attention opens for this watchlist (not every digest poll)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, watchlist.watchlist_id]);

  const checkedAt = localChecked ?? digest?.last_checked_at ?? null;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-mint-400">
            Since you last checked
          </p>
          <h2 className="font-display text-4xl text-white">{watchlist.name}</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Mode: {(digest?.market_data_mode ?? "replay").toUpperCase()}
            {checkedAt ? ` · Last checked ${formatIst(checkedAt)}` : " · Not checked yet"}
          </p>
          {digest?.summary?.headline ? (
            <p className="mt-2 max-w-xl text-sm leading-snug text-[#d7e0ef]">
              {digest.summary.headline}
            </p>
          ) : null}
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className="rounded-md border border-[var(--line)] px-2 py-1 text-xs text-[var(--muted)]">
              {connection === "live"
                ? "Live"
                : connection === "polling"
                  ? "Polling fallback"
                  : "Connecting…"}
            </span>
            <StaleDataBadge
              ageSeconds={digest?.data_age_seconds ?? null}
              mode={digest?.market_data_mode}
            />
          </div>
        </div>
        <div className="rounded-lg border border-[var(--line)] bg-ink-900/50 px-4 py-3 text-xs text-[var(--muted)]">
          <p>High {digest?.summary.high_attention ?? 0}</p>
          <p>Watch {digest?.summary.worth_watching ?? 0}</p>
          <p>Notable {digest?.summary.notable ?? 0}</p>
          <button
            type="button"
            onClick={() => void onResetDemo()}
            className="mt-2 text-mint-400 underline"
          >
            Reset demo novelty
          </button>
        </div>
      </header>

      {/* Lead with ignored — best aha for judges (attention is scarce) */}
      <IgnoredStrip items={digest?.ignored ?? []} />

      {!digest || digest.items.length === 0 ? (
        <div className="rounded-xl border border-[var(--line)] bg-ink-900/40 p-8 text-center">
          <p className="font-display text-3xl text-white">You&apos;re caught up.</p>
          <p className="mt-2 text-sm text-[var(--muted)]">
            {digest?.summary?.empty_hint ??
              "No novel attention items — or sensitivity filtered them out."}
          </p>
          {(digest?.summary?.ignored_count ?? 0) > 0 ? (
            <p className="mt-2 text-xs text-[var(--muted)]">
              {digest!.summary.ignored_count} name(s) explained above under What we ignored.
            </p>
          ) : null}
        </div>
      ) : (
        <div className="space-y-4">
          {(digest.summary.hidden_high ?? 0) > 0 ? (
            <p className="rounded-lg border border-signal-high/30 bg-signal-high/10 px-3 py-2 text-xs text-signal-high">
              +{digest.summary.hidden_high} more High attention item(s) beyond top-K — raise Top-K
              or clear lower cards.
            </p>
          ) : null}
          {digest.items.map((item) => (
            <AttentionCard
              key={item.event_id}
              item={item}
              onMarkSeen={onMarkSeen}
              onFeedback={onFeedback}
            />
          ))}
        </div>
      )}

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-white">Persisted prices (engine input)</h3>
        <WatchlistPrices
          token={token}
          watchlistId={watchlist.watchlist_id}
          refreshKey={refreshKey}
        />
      </section>
    </div>
  );
}

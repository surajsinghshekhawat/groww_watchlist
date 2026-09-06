"use client";

import { useEffect, useState } from "react";

import {
  addInstrument,
  removeInstrument,
  searchInstruments,
  type WatchlistResponse,
} from "@/lib/api";
import { IntentWatchlistBuilder } from "@/components/IntentWatchlistBuilder";

type SearchHit = Awaited<ReturnType<typeof searchInstruments>>[number];

export function WatchlistEditor({
  token,
  watchlist,
  lists,
  onChanged,
  onWatchlistCreated,
  onSelectWatchlist,
}: {
  token: string;
  watchlist: WatchlistResponse;
  lists?: WatchlistResponse[];
  onChanged: (next: WatchlistResponse) => void;
  onWatchlistCreated?: (next: WatchlistResponse) => void;
  onSelectWatchlist?: (id: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [note, setNote] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (query.trim().length < 1) {
      setHits([]);
      return;
    }
    const t = setTimeout(() => {
      void searchInstruments(token, query.trim())
        .then(setHits)
        .catch((err) => setError(err instanceof Error ? err.message : "Search failed"));
    }, 250);
    return () => clearTimeout(t);
  }, [query, token]);

  const owned = new Set(watchlist.instruments.map((i) => i.instrument_id));

  async function onAdd(hit: SearchHit) {
    setBusy(true);
    setError(null);
    try {
      const next = await addInstrument(
        token,
        watchlist.watchlist_id,
        hit.instrument_id,
        watchlist.version,
        note.trim() || undefined
      );
      onChanged(next);
      setQuery("");
      setNote("");
      setHits([]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Could not add";
      setError(msg);
      // Stale version is common — ask parent to reload then user can retry
      if (msg.toLowerCase().includes("version") || msg.toLowerCase().includes("conflict")) {
        setError(msg + " — refresh the Watchlist tab / page and try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function onRemove(instrumentId: string) {
    setBusy(true);
    setError(null);
    try {
      const next = await removeInstrument(
        token,
        watchlist.watchlist_id,
        instrumentId,
        watchlist.version
      );
      onChanged(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="font-display text-3xl text-white">Watchlist</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Multiple lists work like playlists — pick which one Attention/Alerts use right now. Describe
          an intent to preview names, then create a new list when you are happy.
        </p>
      </div>

      {lists && lists.length > 0 && onSelectWatchlist ? (
        <label className="flex flex-wrap items-center gap-2 text-xs text-[var(--muted)]">
          Active playlist
          <select
            className="rounded-md border border-[var(--line)] bg-ink-950 px-3 py-2 text-sm text-white"
            value={watchlist.watchlist_id}
            onChange={(e) => onSelectWatchlist(e.target.value)}
          >
            {lists.map((l) => (
              <option key={l.watchlist_id} value={l.watchlist_id}>
                {l.name} ({l.instruments.length})
              </option>
            ))}
          </select>
        </label>
      ) : null}

      <IntentWatchlistBuilder
        token={token}
        onCreated={(created) => {
          onWatchlistCreated?.(created);
          onChanged(created);
        }}
      />

      <div className="rounded-xl border border-[var(--line)] bg-ink-900/40 p-5 space-y-3">
        <label className="block text-xs text-[var(--muted)]">
          Search
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search e.g. WIPRO, SBIN…"
            className="mt-1 w-full rounded-md border border-[var(--line)] bg-ink-950 px-3 py-2 text-sm text-white"
            disabled={busy}
          />
        </label>
        <label className="block text-xs text-[var(--muted)]">
          Note (why add?)
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="e.g. Watching post-earnings residual vs sector"
            className="mt-1 w-full rounded-md border border-[var(--line)] bg-ink-950 px-3 py-2 text-sm text-white"
            maxLength={500}
            disabled={busy}
          />
        </label>
        {hits.length > 0 ? (
          <ul className="max-h-48 overflow-auto rounded-md border border-[var(--line)] bg-ink-950">
            {hits.map((hit) => {
              const already = owned.has(hit.instrument_id);
              return (
                <li
                  key={hit.instrument_id}
                  className="flex items-center justify-between gap-2 border-b border-[var(--line)] px-3 py-2 text-sm last:border-0"
                >
                  <div>
                    <span className="text-white">{hit.symbol}</span>
                    <span className="ml-2 text-xs text-[var(--muted)]">{hit.company_name}</span>
                  </div>
                  <button
                    type="button"
                    disabled={busy || already || hit.is_index}
                    onClick={() => void onAdd(hit)}
                    className="shrink-0 rounded-md bg-mint-500/20 px-2 py-1 text-xs text-mint-400 disabled:opacity-40"
                  >
                    {already ? "Added" : hit.is_index ? "Index" : "Add"}
                  </button>
                </li>
              );
            })}
          </ul>
        ) : null}
        {error ? <p className="text-xs text-signal-high">{error}</p> : null}
      </div>

      <ul className="space-y-2">
        <li className="text-xs text-[var(--muted)]">
          {watchlist.instruments.length} symbol{watchlist.instruments.length === 1 ? "" : "s"} on
          this list
        </li>
        {watchlist.instruments.map((inst) => (
          <li
            key={inst.instrument_id}
            className="flex items-start justify-between gap-3 rounded-xl border border-[var(--line)] bg-ink-900/30 px-4 py-3"
          >
            <div>
              <p className="text-sm text-white">
                {inst.symbol}
                <span className="ml-2 text-[var(--muted)]">{inst.company_name}</span>
              </p>
              {inst.note ? (
                <p className="mt-1 text-xs text-mint-400/90">Note: {inst.note}</p>
              ) : (
                <p className="mt-1 text-xs text-[var(--muted)]">No note</p>
              )}
            </div>
            <button
              type="button"
              disabled={busy}
              onClick={() => void onRemove(inst.instrument_id)}
              className="text-xs text-[var(--muted)] underline hover:text-signal-high"
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

"use client";

import { useState } from "react";

import {
  createWatchlist,
  deleteWatchlist,
  renameWatchlist,
  type WatchlistResponse,
} from "@/lib/api";

export function WatchlistManager({
  token,
  lists,
  activeId,
  onSelect,
  onListsChanged,
}: {
  token: string;
  lists: WatchlistResponse[];
  activeId: string;
  onSelect: (id: string) => void;
  onListsChanged: (lists: WatchlistResponse[]) => void;
}) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const active = lists.find((l) => l.watchlist_id === activeId) ?? lists[0];

  async function onCreate() {
    if (!name.trim()) return;
    setError(null);
    try {
      const created = await createWatchlist(token, name.trim());
      onListsChanged([...lists, created]);
      onSelect(created.watchlist_id);
      setName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    }
  }

  async function onRename() {
    if (!active) return;
    const next = window.prompt("Rename watchlist", active.name);
    if (!next?.trim()) return;
    try {
      const updated = await renameWatchlist(
        token,
        active.watchlist_id,
        next.trim(),
        active.version
      );
      onListsChanged(lists.map((l) => (l.watchlist_id === updated.watchlist_id ? updated : l)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rename failed");
    }
  }

  async function onDelete() {
    if (!active || lists.length <= 1) {
      setError("Keep at least one watchlist.");
      return;
    }
    if (!window.confirm(`Delete “${active.name}”?`)) return;
    try {
      await deleteWatchlist(token, active.watchlist_id);
      const next = lists.filter((l) => l.watchlist_id !== active.watchlist_id);
      onListsChanged(next);
      onSelect(next[0].watchlist_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <select
        className="rounded-md border border-[var(--line)] bg-ink-950 px-2 py-1.5 text-white"
        value={activeId}
        onChange={(e) => onSelect(e.target.value)}
      >
        {lists.map((l) => (
          <option key={l.watchlist_id} value={l.watchlist_id}>
            {l.name}
          </option>
        ))}
      </select>
      <button type="button" className="underline text-[var(--muted)]" onClick={() => void onRename()}>
        Rename
      </button>
      <button type="button" className="underline text-[var(--muted)]" onClick={() => void onDelete()}>
        Delete
      </button>
      <input
        className="rounded-md border border-[var(--line)] bg-ink-950 px-2 py-1.5 text-white"
        placeholder="New list name"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <button
        type="button"
        className="rounded-md bg-mint-500/20 px-2 py-1.5 text-mint-400"
        onClick={() => void onCreate()}
      >
        Create
      </button>
      {error ? <span className="text-signal-high">{error}</span> : null}
    </div>
  );
}

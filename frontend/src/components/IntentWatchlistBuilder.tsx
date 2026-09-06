"use client";

import { FormEvent, useMemo, useState } from "react";

import {
  confirmWatchlistFromIntent,
  previewWatchlistFromIntent,
  type IntentPreview,
  type WatchlistResponse,
} from "@/lib/api";

const EXAMPLES = [
  "top stocks right now 4",
  "Private banks I should watch around filings",
  "IT services peers of TCS and Infosys",
  "Energy and industrials for the morning session",
];

export function IntentWatchlistBuilder({
  token,
  onCreated,
}: {
  token: string;
  onCreated: (watchlist: WatchlistResponse) => void;
}) {
  const [prompt, setPrompt] = useState(EXAMPLES[0]);
  const [name, setName] = useState("");
  const [preview, setPreview] = useState<IntentPreview | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const allIds = useMemo(
    () => preview?.matches.map((m) => m.instrument_id) ?? [],
    [preview]
  );

  async function onPreview(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setPreview(null);
    try {
      const result = await previewWatchlistFromIntent(token, prompt.trim());
      setPreview(result);
      setName(result.proposed_name);
      setSelected(new Set(result.matches.map((m) => m.instrument_id)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preview failed");
    } finally {
      setBusy(false);
    }
  }

  async function onConfirm() {
    if (!preview || selected.size === 0) return;
    setBusy(true);
    setError(null);
    try {
      const result = await confirmWatchlistFromIntent(token, {
        name: name.trim() || preview.proposed_name,
        instrument_ids: [...selected],
        // Prefer short prompt-based note, not long planner rationale
        note: `Watching: ${prompt.trim().slice(0, 120)}`,
        prompt: prompt.trim(),
      });
      onCreated(result.watchlist);
      setPreview(null);
      setSelected(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="space-y-3 rounded-xl border border-mint-500/25 bg-mint-500/5 p-5">
      <div>
        <h3 className="text-sm font-semibold text-white">Describe a watchlist</h3>
        <p className="mt-1 text-xs leading-relaxed text-[var(--muted)]">
          Step 1 — preview related names from the catalog. Step 2 — confirm to create a{" "}
          <strong className="font-medium text-white">new</strong> watchlist (like a playlist). The
          LLM never invents tickers or scores attention.
        </p>
      </div>

      <form onSubmit={(e) => void onPreview(e)} className="space-y-3">
        <textarea
          className="min-h-[88px] w-full rounded-md border border-[var(--line)] bg-ink-950 px-3 py-2 text-sm text-white"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          disabled={busy}
          maxLength={800}
          required
        />
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              disabled={busy}
              onClick={() => setPrompt(ex)}
              className="rounded-md border border-[var(--line)] px-2 py-1 text-[10px] text-[var(--muted)] hover:text-white"
            >
              {ex}
            </button>
          ))}
        </div>
        <button
          type="submit"
          disabled={busy || prompt.trim().length < 8}
          className="rounded-md bg-mint-500/25 px-3 py-2 text-xs text-mint-400 disabled:opacity-50"
        >
          {busy && !preview ? "Finding matches…" : "Preview related stocks"}
        </button>
      </form>

      {preview ? (
        <div className="space-y-3 rounded-md border border-[var(--line)] bg-ink-950/60 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs text-white">{preview.rationale}</p>
            <span className="text-[10px] uppercase tracking-wide text-[var(--muted)]">
              {preview.model === "llm" ? "LLM + catalog" : "Catalog heuristic"}
            </span>
          </div>
          <label className="block text-xs text-[var(--muted)]">
            New watchlist name
            <input
              className="mt-1 w-full rounded-md border border-[var(--line)] bg-ink-950 px-3 py-2 text-sm text-white"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={busy}
            />
          </label>
          <div className="flex flex-wrap gap-2 text-[10px] text-[var(--muted)]">
            <button
              type="button"
              className="underline"
              onClick={() => setSelected(new Set(allIds))}
            >
              Select all
            </button>
            <button type="button" className="underline" onClick={() => setSelected(new Set())}>
              Clear
            </button>
          </div>
          <ul className="space-y-2">
            {preview.matches.map((m) => (
              <li key={m.instrument_id}>
                <label className="flex cursor-pointer items-start gap-3 rounded-md border border-[var(--line)] px-3 py-2 text-xs hover:bg-ink-900/50">
                  <input
                    type="checkbox"
                    className="mt-0.5"
                    checked={selected.has(m.instrument_id)}
                    onChange={() => toggle(m.instrument_id)}
                    disabled={busy}
                  />
                  <span>
                    <span className="font-semibold text-white">{m.symbol}</span>
                    <span className="ml-2 text-[var(--muted)]">{m.company_name}</span>
                    <span className="mt-0.5 block text-[10px] text-[var(--muted)]">
                      {m.sector} · {m.industry}
                    </span>
                  </span>
                </label>
              </li>
            ))}
          </ul>
          <button
            type="button"
            disabled={busy || selected.size === 0 || !name.trim()}
            onClick={() => void onConfirm()}
            className="rounded-md bg-mint-500/30 px-3 py-2 text-xs font-medium text-mint-400 disabled:opacity-50"
          >
            {busy ? "Creating…" : `Create new watchlist (${selected.size})`}
          </button>
        </div>
      ) : null}

      {error ? <p className="text-xs text-signal-high">{error}</p> : null}
    </div>
  );
}

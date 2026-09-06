"use client";

import { PushSettings } from "@/components/PushSettings";
import { SensitivityControl } from "@/components/SensitivityControl";
import { WatchlistManager } from "@/components/WatchlistManager";
import type { WatchlistResponse } from "@/lib/api";

export function SettingsPanel({
  token,
  lists,
  activeId,
  onSelect,
  onListsChanged,
  onSensitivityChanged,
  onLogout,
}: {
  token: string;
  lists: WatchlistResponse[];
  activeId: string;
  onSelect: (id: string) => void;
  onListsChanged: (lists: WatchlistResponse[]) => void;
  onSensitivityChanged?: () => void;
  onLogout: () => void;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-3xl text-white">Settings</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Sensitivity controls which severities appear in Attention and Alerts. Push keeps you
          informed when the tab is closed.
        </p>
      </div>

      <section className="space-y-4 rounded-xl border border-[var(--line)] bg-ink-900/40 p-5">
        <h3 className="text-sm font-semibold text-white">Attention sensitivity</h3>
        <SensitivityControl token={token} onChanged={onSensitivityChanged} />
        <p className="text-xs text-[var(--muted)]">
          LOW = more items (NOTABLE+). MEDIUM = WORTH_WATCHING+. HIGH = HIGH only.
        </p>
      </section>

      <PushSettings token={token} />

      <section className="space-y-4 rounded-xl border border-[var(--line)] bg-ink-900/40 p-5">
        <h3 className="text-sm font-semibold text-white">Watchlists</h3>
        <WatchlistManager
          token={token}
          lists={lists}
          activeId={activeId}
          onSelect={onSelect}
          onListsChanged={onListsChanged}
        />
      </section>

      <button
        type="button"
        onClick={onLogout}
        className="rounded-md border border-signal-high/40 px-4 py-2 text-sm text-signal-high"
      >
        Sign out
      </button>
    </div>
  );
}

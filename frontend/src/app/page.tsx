import { ApiStatus } from "@/components/ApiStatus";
import { WatchlistApp } from "@/components/WatchlistApp";

export default function HomePage() {
  return (
    <main className="mx-auto min-h-screen max-w-4xl px-6 py-10">
      <header className="mb-8 flex flex-wrap items-start justify-between gap-4 border-b border-[var(--line)] pb-6">
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-[0.2em] text-mint-400">
            Groww CODE 2026 · Demo workspace
          </p>
          <h1 className="font-display text-5xl leading-tight text-white">
            Smart Market Watchlist
          </h1>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-[var(--muted)]">
            Market tape shows simulated live motion. Watchlist holds what you track.
            Attention ranks what deserves focus. Alerts notify on high-value events.
          </p>
        </div>
        <ApiStatus />
      </header>

      <WatchlistApp />
    </main>
  );
}

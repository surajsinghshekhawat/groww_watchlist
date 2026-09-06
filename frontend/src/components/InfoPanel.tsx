"use client";

import type { ReactNode } from "react";

export function InfoPanel() {
  return (
    <div className="space-y-8">
      <header>
        <p className="text-xs uppercase tracking-[0.2em] text-mint-400">Product brief</p>
        <h2 className="mt-1 font-display text-4xl text-white">How Smart Market Watchlist works</h2>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[var(--muted)]">
          Groww already shows prices. This product decides <em>what deserves attention</em> after
          your last check — a scarce, novel, trustworthy set — and shows what it refused to surface.
          It does not predict price or issue buy/sell advice.
        </p>
      </header>

      <Section title="Core formula">
        <p>
          <code className="text-mint-400">ATTENTION = SIGNIFICANCE × NOVELTY × CONFIDENCE</code>
        </p>
        <ul className="mt-3 list-disc space-y-2 pl-5">
          <li>
            <strong className="text-white">Significance</strong> — how unusual the move is vs noise,
            volume, peers, and filings. Severity labels stay discrete (Notable / Worth watching /
            High); the numeric score is <em>continuous inside each band</em> so two Worth-watching
            names can still differ.
          </li>
          <li>
            <strong className="text-white">Novelty</strong> — whether you have already acknowledged
            this event state. Mark seen → novelty collapses until severity escalates. Feedback
            (Useful / Noise / Already knew) records honest labels for tuning; Noise and Already knew
            also clear the card.{" "}
            <em className="text-[var(--muted)]">
              v1 novelty is per user+instrument across all playlists (marking seen on one list
              clears the same name on others).
            </em>
          </li>
          <li>
            <strong className="text-white">Confidence</strong> — data freshness and source agreement.
            Cards show a one-line breakdown (e.g. single source vs DATA_CONFLICT). Replay can demo
            conflict via <code className="text-mint-400">DEMO_CONFLICT_SYMBOL</code>.
          </li>
        </ul>
        <p className="mt-3">
          If any factor is near zero, attention collapses. That is intentional: attention is scarce.
        </p>
      </Section>

      <Section title="Detectors (what we measure)">
        <ul className="list-disc space-y-2 pl-5">
          <li>Price anomaly (robust z / MAD-style deviation)</li>
          <li>Relative volume (RVOL) vs time-of-day baseline</li>
          <li>Market residual and sector residual (idiosyncratic vs beta)</li>
          <li>CUSUM change-point flag (persistence of the move)</li>
          <li>Corporate filings / information evidence from a local demo corpus</li>
        </ul>
        <p className="mt-3">
          Severity fusion maps evidence into LOW → NOTABLE → WORTH_WATCHING → HIGH. The Attention
          tab leads with a one-line digest headline and <em>What we ignored</em> before ranked cards.
          Sensitivity in Settings raises the floor of what enters Attention and Alerts.
        </p>
      </Section>

      <Section title="Identity & state">
        <p>
          Instruments are tracked by stable <code className="text-mint-400">instrument_id</code>, not
          ticker strings alone. Events dedupe and escalate in place so live ingest does not spawn
          duplicate cards. Mark seen clears Attention for that name and the matching alert until a
          true escalation returns.
        </p>
      </Section>

      <Section title="Explanations, RAG, and the LLM">
        <ul className="list-disc space-y-2 pl-5">
          <li>
            Template explanations are built only from evidence fields (returns, RVOL, residuals,
            filing ids).
          </li>
          <li>
            <strong className="text-white">RAG</strong> retrieves symbol-scoped chunks from{" "}
            <code className="text-mint-400">data/filings/docs</code>. Cross-ticker bleed is rejected.
          </li>
          <li>
            <strong className="text-white">LLM (Groq / Gemini)</strong> may narrate High cards only.
            It never invents numbers, never sets severity, and never overrides novelty.
          </li>
          <li>Retrieval chips in the UI are provenance — what was retrieved, not decoration.</li>
        </ul>
      </Section>

      <Section title="NLP → watchlist">
        <p>
          On the Watchlist tab, you can describe an intent in plain language (“private banks around
          filings”). A planner model returns structured symbols/sectors constrained to the live
          instrument catalog. Matching is deterministic. If the LLM is offline, a keyword heuristic
          against the same catalog still works. The planner does not score attention.
        </p>
      </Section>

      <Section title="Alerts & Web Push">
        <ul className="list-disc space-y-2 pl-5">
          <li>In-app Alerts are sensitivity-gated and unread-first.</li>
          <li>Mark seen on Attention clears the related alert.</li>
          <li>
            <strong className="text-white">Web Push (VAPID)</strong> delivers OS notifications when
            the tab is closed (browser may still be running). Enable under Settings. This is the web
            analogue of FCM; native APNs/FCM for mobile apps is a later Groww-surface integration.
          </li>
          <li>While the app is open, WebSocket + polling keep digest and alerts near real-time.</li>
        </ul>
      </Section>

      <Section title="Demo data honesty">
        <p>
          This workspace defaults to **replay + live-sim** so judges do not need a licensed
          exchange feed. Optional <code className="text-mint-400">MARKET_DATA_MODE=yahoo</code>{" "}
          pulls delayed NSE quotes via yfinance into the same S×N×C pipeline — keep{" "}
          <code className="text-mint-400">replay</code> for the scripted HDFC story. Eval:{" "}
          <code className="text-mint-400">python -m app.eval</code>.
        </p>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-[var(--line)] bg-ink-900/40 p-5">
      <h3 className="text-sm font-semibold text-white">{title}</h3>
      <div className="mt-3 text-sm leading-relaxed text-[var(--muted)]">{children}</div>
    </section>
  );
}

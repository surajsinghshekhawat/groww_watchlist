# Smart Market Watchlist — Complete Project Reference

**Groww CODE 2026**  
**Document purpose:** Single long-form reference covering product thesis, architecture, math, features, integrations, optional paths, and competition honesty.  
**Status of product:** Competition demo-ready (Tier 1 + Tier 2). Default data mode: **`replay`**.  
**Last updated:** 2026-09-05  

If you only need a short pitch, read [`README.md`](../README.md) and [`DEMO.md`](./DEMO.md). This file is the deep cut.

---

## Table of contents

1. [Executive summary](#1-executive-summary)  
2. [Problem & product thesis](#2-problem--product-thesis)  
3. [Non-goals & design principles](#3-non-goals--design-principles)  
4. [Core formula & scoring math](#4-core-formula--scoring-math)  
5. [Detectors & evidence math](#5-detectors--evidence-math)  
6. [Evidence fusion & severity](#6-evidence-fusion--severity)  
7. [End-to-end pipeline](#7-end-to-end-pipeline)  
8. [System architecture](#8-system-architecture)  
9. [Data model](#9-data-model)  
10. [Market data providers](#10-market-data-providers)  
11. [Features (complete inventory)](#11-features-complete-inventory)  
12. [Frontend UX map](#12-frontend-ux-map)  
13. [API surface](#13-api-surface)  
14. [LLM, RAG, NLP](#14-llm-rag-nlp)  
15. [Notifications & Web Push](#15-notifications--web-push)  
16. [Feedback loop](#16-feedback-loop)  
17. [Security](#17-security)  
18. [Configuration & thresholds](#18-configuration--thresholds)  
19. [Demo fixtures, calibration & eval](#19-demo-fixtures-calibration--eval)  
20. [Optional / deferred / Tier 3](#20-optional--deferred--tier-3)  
21. [Strategy & product thinking](#21-strategy--product-thinking)  
22. [Competition framing](#22-competition-framing)  
23. [How to run](#23-how-to-run)  
24. [Repository map](#24-repository-map)  
25. [Glossary](#25-glossary)  

---

## 1. Executive summary

**Smart Market Watchlist** is a **state-aware attention-ranking engine** for equity watchlists. It does not replace Groww’s price UI. It answers a different question:

> Out of everything that happened on *my* list while I was away, what is the smallest, highest-value set I need to see — and can you prove, in one sentence, why each item made the cut?

The engine ranks open market events with:

\[
\text{ATTENTION} = \text{SIGNIFICANCE} \times \text{NOVELTY} \times \text{CONFIDENCE}
\]

- **Significance** — how unusual / important the move is *objectively* (detectors + fusion).  
- **Novelty** — whether *this user* has already acknowledged *this event state*.  
- **Confidence** — whether the underlying price data is fresh and consistent enough to trust.

An optional LLM may **narrate** evidence. It **never** chooses significance, severity, or attention. NLP may help build a watchlist from natural language, but tickers are matched only against a catalog. RAG retrieves local demo filings for provenance chips.

The **judge path** uses **`MARKET_DATA_MODE=replay`**: seeded session data + an in-process live-sim tape. Optional Yahoo Finance delayed quotes exist behind a flag; Groww’s paid Trade API is not required for the demo.

---

## 2. Problem & product thesis

### 2.1 What brokers already do

| Capability | Typical broker / Groww surface |
|------------|--------------------------------|
| Live LTP / % change | Strong |
| Static price / % alerts | Strong |
| News feeds | Often global, not list-aware |
| “What moved while I was away that *matters*?” | Weak |
| “Did I already see this exact story?” | Weak |
| “Prove why this interrupt beat market noise” | Weak |

### 2.2 The gap

Retail and semi-pro traders return after minutes or hours. Existing tools answer:

- “What is the price now?”  
- “Did X% trip?”

They do **not** answer:

- Was the move unusual *for that stock*?  
- Was it just beta to Nifty / sector?  
- Is there corroborating volume / persistence / filing?  
- Have I already acknowledged this event state?  
- How trustworthy is the data feeding this alert?

### 2.3 Product bet

This is **attention ranking with memory**, not forecasting.

Users return → system must:

1. Know what changed on their instruments  
2. Judge unusualness vs history  
3. Compare to market and sector context  
4. Check persistence and information corroboration  
5. Assess data trustworthiness  
6. Know whether *this user* already saw *this event state*  
7. Rank a small top-K set  
8. Explain each item from verified evidence only  
9. Show what was deliberately ignored (negative space)

### 2.4 Primary user loop

```
OBSERVATION → FEATURE → ANOMALY → EVENT → EVIDENCE
  → SIGNIFICANCE → USER STATE → NOVELTY → CONFIDENCE
  → ATTENTION → RANK → EXPLAIN → (optional FEEDBACK)
```

UI hierarchy:

1. **What changed?**  
2. **Why does it matter?**  
3. **How confident are we?**  
4. **What did we refuse to show?**

---

## 3. Non-goals & design principles

### 3.1 Explicit non-goals

We will **not** build (for this product / competition):

- Next-price prediction (LSTM / Transformer / “will rise”)  
- Trading bot / auto buy-sell  
- Full RSI/MACD technical-indicator suite as the product  
- Ungrounded LLM “analyst” that invents numbers or sets scores  
- RL personalization of ranking  
- Kubernetes / Kafka / microservice sprawl for a demo  

### 3.2 Load-bearing rules

| Rule | Why |
|------|-----|
| Time-away must **not** inflate significance | Absence is user behavior, not a market fact |
| Novelty is event-state-aware | Escalation (NOTABLE → HIGH) must resurface; same severity after mark-seen must not |
| LLM never judges significance | Unreliable and unexplainable |
| Never key identity on ticker string alone | Renames / dual listings orphan watchlists — use `instrument_id` |
| Stale / conflicted data lowers confidence | Prevents confident false alerts |
| Show refusals | Trust comes from what you *don’t* alert |

### 3.3 Why not a black-box “meaningful move” classifier?

There is **no public ground-truth dataset** of “meaningful vs not” at retail watchlist scale. That is a documented data gap, not an oversight.

Therefore v1 uses an **interpretable, evidence-based** system (rules + robust statistics). ML (Isolation Forest, FinBERT, etc.) may later act only as candidate generators / rerankers — never as the sole judge of attention. User feedback (`useful` / `noise` / `already_knew`) is the honest path to labels.

---

## 4. Core formula & scoring math

### 4.1 Attention

Implemented in `backend/app/scoring/attention.py`:

\[
A = S \cdot N \cdot C
\]

with \(A, S, N, C \in [0, 1]\) (clamped).

```python
score = significance * novelty * max(0.0, min(1.0, confidence))
```

**Implication:** if any factor is near zero, attention collapses. That is intentional — attention is scarce.

### 4.2 Significance \(S\)

Significance is **objective only** — no user memory.

Severity labels stay discrete (LOW / NOTABLE / WORTH_WATCHING / HIGH) for UI and fusion.  
**Numeric \(S\) is continuous inside each band** from how far past fusion thresholds the evidence sits (`significance_continuous` in `app/scoring/significance.py`):

| Severity | \(S\) range (continuous) | Legacy mid-weight |
|----------|--------------------------|-------------------|
| LOW | 0.05 – 0.22 | 0.1 |
| NOTABLE | 0.25 – 0.52 | 0.4 |
| WORTH_WATCHING | 0.55 – 0.85 | 0.7 |
| HIGH | 0.86 – 1.0 | 1.0 |

**Evidence excess** blends how far z / RVOL / residuals sit past thresholds, plus CUSUM / filing boosts. Two WORTH_WATCHING names can share a tier label and still show different Attention scores.

Severity itself comes from **evidence fusion** (Section 6), not from the LLM.

### 4.3 Novelty \(N\)

Event-state-aware novelty (`app/scoring/novelty.py`), keyed by `event_id` in the user’s `WatchlistSnapshot.last_seen_event_states`:

| Situation | \(N\) |
|-----------|-------|
| Never seen this event | **1.0** |
| Seen at **same** severity (even if version ticks from ingest) | **0.0** |
| Severity **rose** vs what was seen | **0.9** |
| Escalated status with unseen higher severity path | **~0.8–0.85** |
| Version bump alone without severity rise | **0.0** (stays hidden) |

**Mark seen** writes severity + version into the snapshot for all open/escalated sibling events on that instrument (so demo duplicates don’t leave a twin card).

**Reset demo novelty** clears seen-state for demos.

### 4.4 Confidence \(C\)

\[
C = \text{freshness} \times \text{agreement} \times \text{completeness}
\]

(`app/scoring/confidence.py`)

**Freshness** (depends on `MARKET_DATA_MODE`):

| Mode | Behavior |
|------|----------|
| `replay` / `mock` | Freshness forced to **1.0** (recorded session must not demote demo HIGH cards by wall-clock age) |
| `yahoo` / `yfinance` | Wider window (at least 120s): 1.0 → 0.7 → 0.3 as age grows |
| true live | Uses `FRESHNESS_LIMIT_SECONDS` (default 30s) bands |

**Agreement:** if multiple prices disagree by more than `SOURCE_CONFLICT_TOLERANCE` (default 1%), agreement → 0.2 and `data_conflict=true`. Single source → agreement 0.8.

**Completeness:** 1.0 if volume present, else 0.7.

Digest cards also expose `confidence_breakdown` — a one-line “why C is X” (e.g. `single source, fresh data → confidence 0.80` or `sources disagree (DATA_CONFLICT) → confidence 0.20`).

**Demo beat:** `DEMO_CONFLICT_SYMBOL=TCS` (default) injects a synthetic second quote so judges can see conflict live without waiting for a real dual-source feed. Keep demo sensitivity at **MEDIUM** so the TCS card is visible.

### 4.5 UI tier mapping

From severity + attention (`ui_tier`):

| Condition | UI tier |
|-----------|---------|
| Severity HIGH and \(A \ge 0.5\) | `HIGH_ATTENTION` |
| Severity WORTH_WATCHING | `WORTH_WATCHING` |
| Severity NOTABLE, or HIGH with \(A < 0.5\) | `NOTABLE` |
| Else | `LOW` |

Digest also filters by user **sensitivity** (LOW / MEDIUM / HIGH) so quieter users see fewer severities.

### 4.6 Digest ranking

Open/escalated events → compute \(S, N, C, A\) → drop LOW / sensitivity misses / market-aligned suppressions into **ignored** → sort by attention → **top-K** (default `TOP_K=5`).

---

## 5. Detectors & evidence math

Pure analytics live under `backend/app/analytics/`. Detectors emit **evidence fields**; they do not directly set attention.

### 5.1 Price anomaly — robust MAD z-score

`price_anomaly.py`

For a horizon window of historical returns \(r_1,\ldots,r_n\) and current return \(r_t\):

\[
\text{median} = \mathrm{median}(r_i),\quad
\text{MAD} = \mathrm{median}(|r_i - \text{median}|)
\]

\[
z = \frac{r_t - \text{median}}{1.4826 \cdot \text{MAD} + \varepsilon}
\]

- Requires ≥ 5 history points; if MAD ≈ 0 → **insufficient data** (no invented signal).  
- Multi-horizon dict (conceptually 5m / 15m / 1h / 1d); **strongest** = max \(|z|\).  
- Percentile bands helper: vs calibrated p90 / p95 / p99 → NORMAL / NOTABLE / UNUSUAL / EXTREME.  
- **Demo path:** when price history is short, a realistic ~1%–scale baseline return window is used (not a near-flat ±0.2% series) so MAD does not collapse and inflate every mid move to z≈14. Display/fusion z is capped (`MAX_PRICE_ANOMALY_Z`, default 8).

In the demo pipeline, a simplified 1d path is used with optional **calibration overlays** for the judge story (Section 19). Set `DEMO_SKIP_CALIBRATION=true` for an uncalibrated moment.

### 5.2 Relative volume (RVOL) — time-of-day normalized

`relative_volume.py`

\[
\text{RVOL} = \frac{V_{\text{now}}}{\mathrm{median}(V_{\text{same TOD bucket}}) + \varepsilon}
\]

- Needs ≥ 3 historical bucket volumes.  
- Compared to threshold `RVOL_THRESHOLD` (default **2.0**) in fusion.

### 5.3 Market / sector context residuals (v1 coarse β)

`market_context.py`

Not live OLS. Uses stored coarse betas on the instrument:

\[
r^{\text{mkt}}_{\text{expected}} = \beta_{\text{mkt}} \cdot r_{\text{mkt}}
\]
\[
r^{\text{sec}}_{\text{expected}} = \beta_{\text{sec}} \cdot r_{\text{sec}}
\]
\[
\text{market residual} = r_{\text{stock}} - r^{\text{mkt}}_{\text{expected}}
\]
\[
\text{sector residual} = r_{\text{stock}} - r^{\text{sec}}_{\text{expected}}
\]

Fusion treats residual magnitude above `CONTEXT_THRESHOLD` (default **0.015**) as context corroboration.

**Digest suppress:** if residuals are tiny *and* no filing *and* price anomaly weak → item can be ignored as **`market_aligned`** (Reliance demo beat).

### 5.4 CUSUM change-point (corroboration only)

`change_point.py`

\[
S_t = \max(0,\, S_{t-1} + (r_t - k))
\]
\[
\text{flagged} \iff S_t > h
\]

Defaults: `CUSUM_K=0.001`, `CUSUM_H=0.02`. Feature-flagged via `ENABLE_CUSUM`.

**Rule:** CUSUM never alone creates a High alert; it only strengthens fusion when market+context already fire.

### 5.5 Information evidence (filings / CA)

`ingestion/filings.py` + `data/filings/demo_filings.json` + markdown corpus under `data/filings/docs/`.

Evidence bundle fields include:

- `filing_present`, `filing_id`, `filing_title`  
- optional corporate action / earnings window flags  

Presence of material information evidence can force **HIGH** in fusion (Section 6).

### 5.6 Peer snapshot

Same-sector peers’ session returns vs the stock (`vs_stock` = peer return − stock return). Displayed on cards for “is this idiosyncratic?” — not a formal scored term in v1 (Tier 3 stretch).

---

## 6. Evidence fusion & severity

`evidence_fusion.py` — **grouped corroboration**, not linear summing of z-scores.

Boolean groups:

| Group | True when |
|-------|-----------|
| `has_market` | \(\|z\| >\) `notable_price_z` (default 2.0) **or** RVOL \(>\) `rvol_threshold` |
| `has_context` | \(\|\text{mkt residual}\|\) or \(\|\text{sec residual}\|\) \(>\) `context_threshold` |
| `has_persistence` | CUSUM flagged (if enabled) |
| `has_information` | Any positive information evidence |

Fusion table:

| Condition | Severity |
|-----------|----------|
| `has_information` | **HIGH** |
| market ∧ context ∧ persistence | **HIGH** |
| market ∧ context | **WORTH_WATCHING** |
| market only | **NOTABLE** |
| else | **LOW** |

This is the heart of “prove it with evidence groups,” not a opaque score soup.

---

## 7. End-to-end pipeline

### 7.1 Logical stages

```
Provider snapshot/history
        ↓
Normalize (instrument_id, CA adjust, source, received_at)
        ↓
PricePoints (Postgres)
        ↓
Detectors → evidence bundle
        ↓
fuse_evidence → Severity
        ↓
upsert MarketEvent + EventEvidence (dedupe / escalate / version)
        ↓
(optional) Notification + Web Push if severity / sensitivity gates
        ↓
Digest: S × N × C → top-K + ignored
        ↓
Explain (template; LLM if HIGH + enabled)
        ↓
REST / WebSocket / UI
```

### 7.2 Code entry points

| Path | Role |
|------|------|
| `app/demo_pipeline.py` | Build deterministic demo events from replay (judge story) |
| `app/services/pipeline.py` | Shared detect → evidence → upsert |
| `app/services/engine_sync.py` | Background: ingest ticks; periodic rescore |
| `app/workers/market_worker.py` | Standalone worker loop using provider factory |
| `app/services/digest_service.py` | Digest, mark-seen, reset, touch-checked |
| `app/events/*` | Store, dedupe, escalation |

### 7.3 Engine sync cadence (app lifespan)

- Price ingest frequently (live-sim ~8s; Yahoo mode slower ~45s to respect rate limits).  
- Full detect/score less often (~ every N cycles) so mark-seen is not wiped every few seconds.

### 7.4 Event dedupe & escalation

- One open “story” per instrument preferred in digest (highest severity, then newest).  
- Escalation bumps version when **severity rises**; same severity refreshes should not resurrect novelty.  
- Dedupe prefers matching type even across demo-day vs live-sim clock gaps.

---

## 8. System architecture

### 8.1 Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js (App Router), React, TypeScript, Tailwind |
| Backend | Python 3.11+, FastAPI, Pydantic, SQLAlchemy 2 (async), Alembic |
| DB | PostgreSQL (source of truth) |
| Cache / fan-out | Redis (pubsub `watchlist:live:{id}`, rate limits) |
| Analytics | NumPy, Pandas, SciPy |
| Optional LLM | Groq or Gemini HTTP APIs |
| Optional quotes | yfinance + curl_cffi |
| Push | Web Push via `pywebpush` + VAPID |
| Infra | Docker Compose for Postgres + Redis |

### 8.2 Persistence split

| Concern | Store |
|---------|--------|
| Users, watchlists, instruments, prices, events, evidence, snapshots, notifications, push subs, feedback | **PostgreSQL** |
| Live fan-out, hot cache, rate limiting | **Redis** |

Redis is never durable SoT for watchlists/events.

### 8.3 Live update path

```
engine_sync / market_worker
    → Postgres events
    → Redis pub/sub
    → WS /ws/watchlists/{id}?token=
    → on failure: client polls digest (active ~8s / background slower)
```

Public demo tape: `/api/v1/market/tape` + `/ws/tape` (live-sim in replay mode).

### 8.4 Identity model

- Permanent key: **`instrument_id` (UUID)**  
- `symbol` is display metadata  
- Watchlist items reference `instrument_id` only  
- Dual-listing / rename safe by design  

---

## 9. Data model (conceptual)

| Entity | Role |
|--------|------|
| `User` | Auth, sensitivity |
| `Instrument` | Equity / index master; betas; sector |
| `Watchlist` / `WatchlistItem` | Playlist + optional **note** |
| `PricePoint` | timestamp, price, volume, source, received_at |
| `MarketEvent` | type, severity, status, version, windows |
| `EventEvidence` | JSON evidence bundle |
| `WatchlistSnapshot` | last_checked_at, last_seen_event_states (novelty memory) |
| `Notification` | In-app attention-gated alerts |
| `PushSubscription` | Web Push endpoints |
| `EventFeedback` | useful / noise / already_knew |

Migrations: `0001` … `0005_event_feedback`.

---

## 10. Market data providers

Factory: `app/ingestion/factory.py` from `MARKET_DATA_MODE`.

| Mode | Provider | Purpose |
|------|----------|---------|
| **`replay`** (default) | Replay fixtures + **live-sim** tape in engine | Judge demo |
| `live` | Live-sim tape as “live-shaped” interface | Demo continuity |
| `mock` | Tests |
| `yahoo` / `yfinance` | Delayed NSE via Yahoo (`.NS`, `^NSEI`) | Optional personal “live-ish” |

Protocol (`RawObservation`): `instrument_id`, `timestamp`, `price`, `volume`, `source`.

Corporate actions: demo catalog adjuster before detectors.

**Honesty:** replay/live-sim are not licensed exchange feeds. Yahoo is unofficial delayed data. Groww Trade API (LTP/quote/holdings) is a future paid upgrade path — not wired as default.

---

## 11. Features (complete inventory)

### 11.1 Identity & watchlists

- Register / login (JWT, Argon2id, rate limits)  
- Watchlist CRUD + optimistic `version` concurrency  
- Add/remove instruments (max size configurable)  
- Instrument search  
- Per-item notes (explanation context only — never boost S)  
- NLP describe-a-watchlist: preview → confirm → **new playlist**  
- Active playlist selector  

### 11.2 Detection & events

- MAD multi-horizon price anomaly (analytics; demo uses calibrated path)  
- TOD RVOL  
- Market + sector residuals (coarse β)  
- CUSUM corroboration (flag)  
- Filings / info evidence (demo corpus)  
- First-class `MarketEvent` + evidence fusion  
- Dedupe + escalation  
- Continuous engine sync / worker path  

### 11.3 Scoring & digest

- Continuous \(S\) inside severity bands + discrete UI labels  
- S / N / C / Attention (with `confidence_breakdown`)  
- Digest **headline** one-liner + **ignored strip** (shown first in UI)  
- Top-K digest with HIGH preference + `hidden_high`  
- Mark-seen / reset-seen / touch-checked (throttled)  
- Template explanations (no stray “SYMBOL, is up…” comma) + optional LLM on HIGH  
- RAG retrieval chips  
- Peer rows  
- Stale / data-conflict badges (`DEMO_CONFLICT_SYMBOL` for talk-track)  
- Sensitivity filter  
- Feedback buttons  
- `DEMO_SKIP_CALIBRATION` for unscripted math beat  

### 11.4 Live & alerts

- WebSocket watchlist channel + polling fallback  
- Market tape UI  
- In-app notifications (severity / sensitivity gated)  
- Web Push (VAPID) when configured  

### 11.5 Security & ops

- Ownership checks (unknown IDs → 404, no IDOR leak)  
- CORS allowlist, security headers, validation  
- Docker Compose, Alembic, seed, demo_pipeline, eval  
- Unit tests (analytics, scoring, authz samples)  

---

## 12. Frontend UX map

| Tab | Job |
|-----|-----|
| **Market** | Live-sim (or Yahoo) tape — grounds the story in prices |
| **Watchlist** | Curate lists, notes, NLP builder |
| **Attention** | Hero: headline, ignored-first, ranked cards (continuous S · N · C + confidence why), evidence, mark-seen, feedback, price rows |
| **Alerts** | Attention-gated notification inbox |
| **Settings** | Sensitivity + push enable |
| **Info** | Judge-facing honesty: formula, RAG, LLM bounds, demo limits |

Login leaves quickly after watchlists load; digest can finish in background so LLM latency doesn’t trap auth.

---

## 13. API surface (summary)

Prefix: `/api/v1`

| Area | Endpoints (representative) |
|------|----------------------------|
| Auth | `POST /register`, `POST /login`, `GET /me` |
| Watchlists | CRUD, items, search, prices |
| NLP | `POST /watchlists/from-intent/preview`, `/confirm` |
| Digest | `GET .../digest`, `POST .../mark-seen`, `reset-seen`, `touch-checked` |
| Feedback | `POST /events/{event_id}/feedback` |
| Notifications | list, mark-read |
| Settings | get/patch sensitivity |
| Push | status, subscribe, unsubscribe, VAPID public key |
| Market | `GET /market/tape` |
| Health | `/health`, `/ready` |
| WS | `/ws/watchlists/{id}?token=`, `/ws/tape` |

Full tables: [`API.md`](./API.md).

---

## 14. LLM, RAG, NLP

### 14.1 LLM (optional)

- Providers: **Groq** (recommended) or **Gemini**  
- Used for:  
  1. Narrating **HIGH** attention cards from evidence JSON + retrieved snippets  
  2. Planning NLP watchlist intents (symbols/sectors JSON)  
- **Forbidden:** setting S/N/C, inventing prices/filings, buy/sell advice  
- Timeouts short so digest/login stay usable; fallback = templates / heuristics  
- Setup: [`LLM.md`](./LLM.md)

### 14.2 RAG

- Local BM25-style keyword retrieval over `data/filings/docs/*.md`  
- Symbol-scoped so another ticker’s filing is not attached  
- Digest path typically **`include_web=False`** (DuckDuckGo exists but is off by default for cards)  
- UI shows retrieval chips separately from the prose  

### 14.3 NLP watchlist

1. User describes intent (“IT peers of TCS…”, “top stocks right now 4”)  
2. LLM (or heuristic fallback) proposes symbols/sectors **from allowed catalog only**  
3. Deterministic resolve → preview → user confirms → **new watchlist**  
4. Notes stored as clean “Watching: …” — never planner diagnostics (“LLM unavailable”)  

Vague “top N” intents fall back to a diversified liquid catalog slate with count enforcement.

---

## 15. Notifications & Web Push

### In-app

Created when events meet severity/sensitivity gates. Alerts UI shows unread; mark-seen can clear matching notifications.

### Web Push

- VAPID keys in `.env`  
- Service worker `frontend/public/sw.js`  
- Subscribe from Settings  
- Docs: [`PUSH.md`](./PUSH.md)  

Away-from-tab alerts when the browser can still wake the SW — not a native mobile FCM stack.

---

## 16. Feedback loop

**Problem:** no public labels for “was this attention useful?”

**Solution:** per-user labels on events:

| Label | Behavior |
|-------|----------|
| `useful` | Persist; card stays |
| `noise` | Persist + mark-seen (leaves digest) |
| `already_knew` | Persist + mark-seen |

Table `event_feedback`; API `POST /events/{id}/feedback`; digest field `user_feedback`.

**Future:** aggregate labels to tune thresholds / sensitivity defaults — better than Isolation Forest cosplay without labels.

---

## 17. Security

See [`SECURITY.md`](./SECURITY.md). Highlights:

- Argon2id passwords  
- JWT access tokens; WS token as query param (documented tradeoff)  
- Ownership on all watchlist/digest routes; missing → **404**  
- Rate limits on auth / digest / mark-seen / feedback  
- CORS allowlist (never `*` with credentials)  
- Security headers (frame deny, etc.)  
- Secrets in `.env` only — never commit keys  

---

## 18. Configuration & thresholds

Centralized in `app/core/config.py` + root `.env`.

| Setting | Default (typical) | Role |
|---------|-------------------|------|
| `MARKET_DATA_MODE` | `replay` | Provider selection |
| `TOP_K` | 5 | Digest size |
| `RVOL_THRESHOLD` | 2.0 | Volume corroboration |
| `CONTEXT_THRESHOLD` | 0.015 | Residual corroboration |
| `NOTABLE_PRICE_Z` | 2.0 | Anomaly corroboration |
| `FRESHNESS_LIMIT_SECONDS` | 30 | Live confidence |
| `SOURCE_CONFLICT_TOLERANCE` | 0.01 | Multi-source disagreement |
| `CUSUM_K` / `CUSUM_H` | 0.001 / 0.02 | Persistence |
| `ENABLE_LLM` | false/true | Narration + NLP planner |
| `ENABLE_CUSUM` | true | Persistence flag |
| `ENABLE_WEB_PUSH` | true | Push sends |
| Severity weights | 0.1 / 0.4 / 0.7 / 1.0 | Map severity → S |

Feature flags also exist for news, rolling OLS, isolation forest, FinBERT (off by default).

---

## 19. Demo fixtures, calibration & eval

### Fixtures

- `data/replay/demo_session.json` — deterministic price path  
- `data/filings/demo_filings.json` + `docs/*.md` — information + RAG  
- Seed instruments: HDFC, Reliance, TCS, INFY, ICICI, SBIN, WIPRO, LT, Nifty indices, …  
- Demo user: `demo@example.com` / `DemoPass123!`  

### Calibration overlays

`pipeline.py` applies **demo calibration** so the judge narrative is stable:

- **HDFCBANK** — strong z, RVOL ~4.1×, CUSUM on, filing path → **HIGH**  
- **RELIANCE** — weak residuals forced market-aligned, no filing → **suppressed**  
- **TCS** — milder anomaly / RVOL → mid tier  

This is intentional demo engineering: the *architecture* is general; the *seed story* is scripted for CODE.

### Eval harness

```bash
cd backend
python -m app.eval
```

Expect **5/5** checks aligned to the demo narrative (HIGH HDFC, Reliance ignored path, etc.).

### Demo pipeline

```bash
python -m app.demo_pipeline
```

Rebuilds events/evidence for the scripted session. Re-run if Attention looks wrong after experiments.

---

## 20. Optional / deferred / Tier 3

| Item | Status | Notes |
|------|--------|-------|
| Yahoo delayed quotes | **Optional flag** | Not judge default |
| Groww Trade API | Not wired | Paid; LTP/holdings upgrade path |
| Rolling OLS residuals | Flagged off | Better β later |
| Isolation Forest | Flagged off | Candidate gen only if ever on |
| FinBERT on filings | Flagged off | Sentiment assist only |
| Peer-divergence scored term | Not formal | Peers are display |
| Feedback → auto threshold tuning | Labels shipped; tuner later | |
| Native mobile push | Out of scope | Web Push only |
| Chrome extension | Deferred | |
| Order placement from Attention | **Never** (non-goal) | |

---

## 21. Strategy & product thinking

### 21.1 Why this wedge for Groww

Groww’s strength is distribution + trading + portfolio. A watchlist that only sorts by % change creates **alert fatigue**. An attention layer:

- Increases session quality (“I open Groww and know where to look”)  
- Fits compliance better than “AI stock tips”  
- Can sit *on top of* existing prices without replacing the broker UI  

### 21.2 Why multiplicative attention

Additive scores let one loud factor dominate. Multiplication encodes: **unusual ∧ new ∧ trustworthy**. Miss any → silence. That matches human triage.

### 21.3 Why show ignored items

Trust is asymmetric. Users forgive a miss more if they understand suppressions (“moved with market”). The ignore strip is part of the product, not debug UI.

### 21.4 Why keep LLM thin

LLMs are excellent narrators and terrible unaudited risk officers. Scoring stays deterministic and testable (`app.eval`). Narration is optional polish on HIGH cards.

### 21.5 Path to a daily trader tool (post-CODE)

1. Licensed or broker live quotes (Groww API if subscribed)  
2. Live corporate filings / announcements linked to `instrument_id`  
3. Real multi-session history for MAD/RVOL  
4. Use feedback aggregates to tune thresholds  
5. Holdings → auto watchlist  
6. Quiet hours + severity matrix for push  

Until then: **replay demo proves the thesis**; Yahoo proves the provider seam.

---

## 22. Competition framing

### Pitch (20 seconds)

> Groww already shows prices. We decide what deserves attention after your last check — Significance × Novelty × Confidence. We show High stories with evidence, and we show what we refused to show. The LLM never sets the score.

### Must-work demo beats

1. Watchlist = input  
2. HDFC → High with evidence  
3. Reliance → market-aligned ignore  
4. Mark seen → novelty memory  
5. (Supporting) feedback / push / NLP / Info tab  

### Mode for the room

```env
MARKET_DATA_MODE=replay
```

Use Incognito if browser extensions break Mark seen.

### Docs for judges

1. [`README.md`](../README.md)  
2. [`DEMO.md`](./DEMO.md)  
3. [`01-PRODUCT.md`](./01-PRODUCT.md)  
4. This file (deep dive)  
5. Canvas: `groww-code-competition`  

---

## 23. How to run

### Prerequisites

- Docker Desktop (Postgres + Redis) or equivalent  
- Python 3.11+, Node 20+  

### Boot

```powershell
docker compose up -d postgres redis
cd backend
python -m pip install -r requirements.txt
alembic upgrade head
python -m app.seed
python -m app.demo_pipeline
python -m app.eval
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
cd frontend
npm install
npm run dev
```

- UI: http://localhost:3000  
- Health: http://localhost:8000/health  
- OpenAPI: http://localhost:8000/docs  
- Login: `demo@example.com` / `DemoPass123!`  

Postgres host port is typically **55432** to avoid clashing with local installs.

---

## 24. Repository map

```
groww - watchlist/
├── README.md                 # Competition entry
├── .env / .env.example
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI + lifespan loops
│   │   ├── api/              # Routes
│   │   ├── analytics/        # MAD, RVOL, context, CUSUM
│   │   ├── scoring/          # S, N, C, attention, fusion
│   │   ├── services/         # digest, pipeline, engine_sync, NLP, push, feedback
│   │   ├── ingestion/        # replay, live-sim, yahoo, filings, CA
│   │   ├── events/           # store, dedupe, escalate
│   │   ├── explanation/      # templates, LLM, RAG
│   │   ├── db/models/        # SQLAlchemy
│   │   └── workers/          # market_worker
│   ├── migrations/
│   └── tests/
├── frontend/
│   ├── src/components/       # Tabs, cards, settings, NLP, push
│   └── public/sw.js          # Service worker
├── data/
│   ├── replay/
│   └── filings/
└── docs/                     # Product + this reference
```

---

## 25. Glossary

| Term | Meaning |
|------|---------|
| Attention | \(S \times N \times C\) ranking score |
| Significance | Objective unusualness from severity / fusion |
| Novelty | User-event-state memory factor |
| Confidence | Data trust factor |
| Residual | Stock return minus β-scaled market/sector return |
| RVOL | Volume vs typical volume for this time-of-day bucket |
| MAD z | Robust z-score using median absolute deviation |
| CUSUM | Cumulative sum change detector (corroboration only) |
| Mark-seen | User acknowledges event state → novelty collapses |
| Ignored strip | Explicit list of suppressions / quiet names |
| Live-sim | In-process simulated tape for demo |
| Replay | Seeded historical session for deterministic demo |
| instrument_id | Stable UUID identity (not ticker PK) |

---

## Closing

This project is a **complete, demoable attention engine**: interpretable math, memory, evidence, refusals, and optional narration — shaped to sit beside Groww’s price surface without pretending to be a predictor or a trading bot.

For the shortest path through the material: **README → DEMO → Attention tab live → this document when judges ask “how does the math work?”**

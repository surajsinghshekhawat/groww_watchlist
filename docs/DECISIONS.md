# Design decisions — considered, shipped, deferred, rejected

**Purpose:** Show judges what we *thought about*, not only what shipped.  
**Product thesis:** Attention ranking (`S × N × C`), not price prediction.

Related: [01-PRODUCT.md](./01-PRODUCT.md) · [03-FEATURES.md](./03-FEATURES.md) · [SUGGESTION-ANALYSIS.md](./SUGGESTION-ANALYSIS.md)

---

## How to read this

| Label | Meaning |
|-------|---------|
| **Shipped** | In the demo / codebase |
| **Deferred** | Makes sense later; skipped for CODE scope / time / honesty |
| **Rejected** | Considered and intentionally **not** doing (product or integrity) |

---

## 1. Core product bets (shipped)

| Decision | Why |
|----------|-----|
| Attention engine, not a charting app | Groww already shows prices; the scarce resource is *attention after last check* |
| `A = S × N × C` (multiplicative) | One weak factor collapses the score — matches triage (“unusual ∧ novel ∧ trustworthy”) |
| Discrete severity **labels** + continuous **S inside band** | UI needs bands; same-tier cards must still differentiate |
| Show **What we ignored** first | Trust requires explaining suppressions (e.g. market-aligned Reliance) |
| LLM **never sets the score** | Optional narration over verified evidence only — avoids fake “AI tips” |
| `instrument_id` as identity, not ticker string | Survives renames / exchange quirks; Groww-shaped data model |
| Replay as **judge default** | Stable HDFC / Reliance story; live markets would flake mid-demo |

---

## 2. Approaches considered → deferred

| Approach | Why it was attractive | Why we deferred |
|----------|----------------------|-----------------|
| **Groww Trade API** (LTP / holdings) | Perfect Groww-context; holdings-aware attention | Paid / no free tier for contest; architecture left provider-shaped instead |
| **Licensed exchange live feed** | “Real-time” credibility | Cost + compliance + demo instability; we ship honest **replay + live-sim** |
| **Rolling OLS market/sector β** | Cleaner residuals than coarse β | Tier 3; won’t save the pitch if continuous S / ignored strip are weak |
| **Isolation Forest / unsupervised “weirdness”** | Extra anomaly candidates | Easy to overfit narrative; only acceptable as *candidate gen* behind a flag — left off |
| **FinBERT on filings** | Sentiment / relevance assist | Needs careful grounding; risk of looking like black-box scoring; RAG + templates enough for CODE |
| **Peer divergence as scored term** | Peers already on cards | Display first; formal weight needs calibration we didn’t want to fake |
| **Feedback → auto-tune thresholds** | Labels (`useful` / `noise` / `already_knew`) exist | Full tuner can surprise mid-demo; labels shipped, adaptive loop later |
| **Sector bundling in digest** | Attention is scarce; group IT names | Non-trivial UX; after ranking quality |
| **Holdings stub (“you hold N shares”)** | Strong Groww wedge | Without real holdings API it becomes theatre; deferred |
| **Retrospective “did HIGH matter?”** | Persuasive if honest | On a *calibrated* replay it can look circular; eval harness instead of fake alpha |
| **Native Android/iOS + FCM/APNs** | Production Groww surface | Out of contest scope; **Web Push** covers closed-tab demo |
| **Chrome extension** | Ambient alerts | Extra surface area; web app + push is enough |
| **Yahoo as default market mode** | Free delayed quotes | Unofficial + flake risk; kept as **optional** `MARKET_DATA_MODE=yahoo` |

---

## 3. Approaches considered → rejected

| Approach | Why rejected |
|----------|----------------|
| **Next-price / “will rise” models** | Non-goal; compliance and product integrity |
| **Buy/sell recommendations or order placement from Attention** | Broker job ≠ attention job; never |
| **LLM decides significance** | Ungrounded analyst theatre; score stays fusion math |
| **From-scratch ML “meaningful move” classifier** | No public ground-truth labels for “deserved attention” |
| **RL personalization** | Overkill + opaque for a CODE demo |
| **Full RSI/MACD/indicator dashboard** | Rebuilds what Groww already does; wrong wedge |
| **Additive “importance” score only** | One loud factor (e.g. % move) dominates; we require multiplicative collapse |
| **Hide ignored / suppressed names** | Looks smart until users distrust silence; transparency is the product |

---

## 4. Stack & delivery choices

| Choice | Alternative considered | Why this |
|--------|------------------------|----------|
| FastAPI + Next.js | Monolith / Flutter | Fast API surface for judges + web demo; matches team strength |
| Postgres + Redis | SQLite only | Ownership, events, snapshots need real persistence; Redis for WS fan-out |
| Interpretable detectors (MAD, RVOL, residuals, CUSUM) | Deep models first | Explainable evidence chips; judges can audit “why” |
| Vercel (UI) + Railway (API/DB/Redis) | Single VPS only | Public HTTPS demo URL with managed pieces |
| Docker Compose for local Postgres/Redis | Fully local installs | Reproducible judge / teammate boot |

---

## 5. Demo honesty (on purpose)

| What judges see | What it is **not** |
|-----------------|--------------------|
| Replay session + live-sim tape | A licensed NSE live feed |
| Demo filings corpus + local RAG | Exhaustive exchange disclosure firehose |
| Optional Groq/Gemini narration | The scoring engine |
| `DEMO_CONFLICT_SYMBOL` (default TCS) | A claim that dual-source feeds are always live in v1 |

If we flip `DEMO_SKIP_CALIBRATION`, the talk-track can show a raw/uncalibrated moment — calibration is a **demo aid**, not hidden “AI magic.”

---

## 6. One-line summary for Q&A

> We scoped for a *defensible attention wedge*: interpretable `S×N×C`, novelty memory, ignored-with-reason, and honest data modes. ML stretch, broker APIs, and prediction were deferred or rejected so the pitch stays clear and trustworthy.

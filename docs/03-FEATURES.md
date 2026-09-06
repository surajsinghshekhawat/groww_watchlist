# 03 — Features

Organized by delivery tier. **Tier 1 must work before Tier 2/3.**

---

## Tier 1 — Must-have

### Watchlist & identity

- [x] Auth (register/login), Argon2id passwords, rate-limited
- [x] Watchlist CRUD (create, rename, delete) — API + UI
- [x] Add/remove instruments (max size configurable, default 100)
- [x] Server-side persistence + `version` optimistic concurrency
- [x] Instrument master with stable `instrument_id` (never ticker as PK)
- [x] Instrument search (`symbol`, name, exchange)

### Market data

- [x] Price points with `timestamp`, `received_at`, `source`, adjusted price
- [x] Split/bonus adjustment before detectors
- [x] Provider abstraction + **replay** / mock / live-sim
- [x] Seeded demo instruments (+ SBIN, WIPRO, LT)

### Detection & events

- [x] Robust MAD multi-horizon price anomaly (5m / 15m / 1h / 1d)
- [x] Time-of-day normalized RVOL (~20 sessions)
- [x] Market **and** sector context residuals (v1 coarse beta)
- [x] First-class persisted `MarketEvent` with severity/status/version
- [x] Evidence fusion with cross-group corroboration
- [x] Event deduplication + escalation
- [x] Continuous worker detect → score → notify path

### Scoring & digest

- [x] Significance continuous inside severity bands (labels stay discrete)
- [x] Confidence (freshness × agreement × completeness) + breakdown line on cards
- [x] Novelty (event-state-aware)
- [x] Attention = S × N × C; top-K ranking + digest headline
- [x] Ignored strip (UI leads with it) + market-aligned / sensitivity reasons
- [x] Demo knobs: `DEMO_CONFLICT_SYMBOL`, `DEMO_SKIP_CALIBRATION`, `MAX_PRICE_ANOMALY_Z`
- [x] `GET .../digest` + `POST .../mark-seen`
- [x] Template grounded explanations
- [x] Watchlist price rows API + UI

### Live & resilience

- [x] WebSocket live updates for owned watchlist
- [x] Polling fallback on WS failure
- [x] Stale-data badge + confidence downgrade
- [x] Data-conflict handling
- [x] Health / ready endpoints
- [x] In-app notifications (HIGH / sensitivity-gated) + Alerts UI

### Security & ops

- [x] Ownership checks (no IDOR via URL user id)
- [x] CORS allowlist, security headers, input validation
- [x] Docker Compose + migrations + seed
- [x] Unit tests for analytics + security tests for authz

---

## Tier 2 — High value after Tier 1

- [x] CUSUM change-point as corroborating persistence
- [x] Corporate action / filing / earnings → information evidence (demo catalog)
- [x] Retrieval-grounded LLM explanations (local paraphraser; template fallback)
- [x] Per-user sensitivity slider (LOW/MEDIUM/HIGH)
- [x] Sector/peer comparison view in UI

---

## Tier 3 — Stretch only

- [ ] Rolling OLS residuals (feature-flagged)
- [ ] Isolation Forest as candidate generator only
- [ ] FinBERT relevance/sentiment on retrieved text
- [ ] Peer-divergence as formal context term
- [x] Feedback loop (“useful / not useful / already knew”) — shipped as Attention labels
- [x] Optional Yahoo delayed quotes (`MARKET_DATA_MODE=yahoo`) — not judge default

---

## Explicitly out of scope

- Next-price prediction models  
- Full technical-indicator dashboard  
- LLM deciding significance  
- Reinforcement-learning personalization  
- From-scratch ML “meaningful” classifier  
- Autonomous trading / buy-sell language  
- Native mobile / Chrome extension (deferred by product choice)

---

## UI feature map (Tier 1)

| Component | Job |
|-----------|-----|
| WatchlistView / Prices | Rows: symbol, price, change, sector, freshness |
| SinceLastChecked / AttentionFeed | Ranked digest tiers |
| AttentionCard | Severity, move, context, RVOL, peers, one-line why |
| EvidencePanel | Expandable machine-readable evidence |
| StaleDataBadge / DataConflictBadge | Resilience visibility |
| EmptyState | “You’re caught up” — never invent activity |
| Demo mode banner | LIVE vs REPLAY clearly labeled |
| NotificationBell | In-app HIGH alerts |
| SensitivityControl | User threshold |
| WatchlistManager | Create / rename / delete lists |

# 06 — Implementation Plan

**Created:** 2026-09-04  
**Status:** Phase 1 done · Phase 2 code done (migrate/seed needs Docker)  
**Goal:** Ship a demoable Tier 1 attention engine with replay, then harden and add Tier 2 behind flags.

---

## Phase 0 — Documentation & planning

**Deliverables**

- [x] Docs index and product / stack / features / methodology / architecture  
- [x] Implementation plan (this file)  
- [x] Development log + changelog initialized  
- [x] Phase-0 plan note  
- [x] Root README pointing to docs  
- [x] Manual task checklist (`docs/09-TASKS.md`)  
- [x] Removed Task Master (not used)

**Exit gate:** User agrees the plan; we start Phase 1 scaffolding. ✅

---

## Phase 1 — Repository & infra skeleton ✅

**Build**

- [x] Monorepo layout: `backend/`, `frontend/`, `data/`, Docker Compose  
- [x] FastAPI hello + health; Next.js app shell  
- [x] Postgres + Redis services (compose defined)  
- [x] `.env.example`, Makefile, `.gitignore`  

**Exit gate:** API health locally; frontend builds; compose ready when Docker Desktop is on. ✅

---

## Phase 2 — Database foundation ← next

**Build**

- SQLAlchemy models (users, instruments, watchlists, items, price_points, market_events, evidence, snapshots)  
- Alembic initial migration  
- Repositories  
- Seed command + demo instruments  

**Exit gate:** Migrations apply; seed loads; models match spec.

---

## Phase 3 — Authentication & authorization

**Build**

- Register/login; Argon2id; JWT or httpOnly cookies  
- Dependency injection of current user  
- Rate limit auth endpoints  

**Exit gate:** Unauthenticated protected routes → 401; security tests start.

---

## Phase 4 — Watchlist CRUD

**Build**

- Full watchlist + instrument membership APIs  
- Version conflicts → 409  
- Ownership checks → 404/403 without leakage  

**Exit gate:** User A cannot access User B; IDOR tests pass.

---

## Phase 5 — Market data + replay

**Build**

- `MarketDataProvider` protocol  
- Replay + Mock providers  
- Normalizer (validate price/volume/timestamps)  
- Replay dataset for demo scenario  

**Exit gate:** Deterministic replay feeds the same pipeline path as live.

---

## Phase 6 — Analytics engines

**Build**

- `price_anomaly.py` — robust z, multi-horizon, percentile bands  
- `relative_volume.py` — time-bucket RVOL  
- `market_context.py` — v1 beta residuals  
- Central config for thresholds  

**Exit gate:** Unit tests for normal/extreme/zero-MAD/insufficient data paths.

---

## Phase 7 — Event pipeline

**Build**

- Detector orchestration  
- Event store, dedupe, escalation  
- Persist evidence bundles  

**Exit gate:** Same underlying move updates one event; severity can escalate.

---

## Phase 8 — Scoring

**Build**

- Evidence fusion, significance, confidence, novelty, attention  
- Top-K ranker  

**Exit gate:** Unit tests for every fusion severity path + novelty edge cases.

---

## Phase 9 — Digest & mark-seen

**Build**

- Digest service + API  
- Mark-seen writes event state into snapshot  
- Template explanations  

**Exit gate:** Demo HDFC ranks HIGH; mark-seen clears; escalation resurfaces.

---

## Phase 10 — WebSockets

**Build**

- Authenticated WS scoped to watchlist instruments  
- Pub/sub fan-out from Redis  
- Client reconnect + polling fallback  

**Exit gate:** Unauthorized WS rejected; live ticks update UI.

---

## Phase 11 — Frontend polish

**Build**

- Attention feed, cards, evidence panel, badges, empty state  
- Demo mode banner (REPLAY vs LIVE)  
- Responsive, accessible tier labels  

**Exit gate:** Judge demo script runnable from UI.

---

## Phase 12 — Tier 2 (flagged)

**Build**

- CUSUM, filings/CA ingestion, optional LLM explain  

**Exit gate:** Flags off → Tier 1 unchanged; flags on → enhanced evidence.

---

## Phase 13 — Security hardening

**Build**

- Headers, CORS review, rate limits on expensive routes  
- Security test suite complete  

**Exit gate:** Checklist in SECURITY.md (to be written in this phase) green.

---

## Phase 14 — Quality gate & demo

**Build**

- Full test run, Docker verify, DEMO.md script  
- ARCHITECTURE/SECURITY/API docs finalized  

**Exit gate:** Spec §118 acceptance criteria satisfied for Tier 1.

---

## Risk register (watch)

| Risk | Mitigation |
|------|------------|
| Scope creep into dashboard/ML | Priority list + Tier gates |
| Live market API unavailable | Replay-first demo |
| LLM flakiness | Template fallback always |
| Time pressure | Ship Phase 1–11 before Tier 2 |

---

## Immediate next step after Phase 0 approval

Start **Phase 1**: scaffold backend/frontend/Docker and prove local boot.

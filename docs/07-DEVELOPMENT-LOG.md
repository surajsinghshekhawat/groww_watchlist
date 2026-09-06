# 07 ? Development Log

Append-only diary of every step. Newest entries at the **bottom**.

---

## 2026-09-04 ? Phase 0 kickoff

### Context

- Greenfield repo (`groww - watchlist`); no existing code.
- User provided Design Spec v2 + Master Implementation Spec.
- Request: understand system, then create proper docs/plans and document every change.

### What we did

- Confirmed product understanding with user (attention engine, not predictor).
- Created documentation structure under `docs/`.
- Wrote product vision, tech stack, features, methodology, architecture overview, implementation plan.
- Initialized this development log and changelog.
- Created Phase 0 plan note.
- Added condensed product docs and implementation plan (no Task Master).
- Added root `README.md` pointing to docs.

### Files created

- `docs/00-INDEX.md`
- `docs/01-PRODUCT.md`
- `docs/02-TECH-STACK.md`
- `docs/03-FEATURES.md`
- `docs/04-METHODOLOGY.md`
- `docs/05-ARCHITECTURE.md`
- `docs/06-IMPLEMENTATION-PLAN.md`
- `docs/07-DEVELOPMENT-LOG.md` (this file)
- `docs/08-CHANGELOG.md`
- `docs/09-TASKS.md`
- `docs/plans/phase-00-documentation.md`
- `README.md`
- `.gitignore` (project baseline)
- `data/seed/`, `data/replay/` (placeholders)

### Decisions

- **Docs-first before scaffolding code** ? user requested plans/docs before implementation.
- **Phase numbering 0?14** aligned with spec workflow + explicit Phase 0 for documentation.
- **Replay-first** as default demo path when live APIs are unavailable.
- **No Task Master** ? manual checklist only.

### Tests run

- None (documentation only).

### Next

1. User reviews docs/plan and approves.
2. Start Phase 1 / Task 1: Docker + FastAPI + Next.js skeleton.

---

## 2026-09-04 ? Dropped Task Master

### What we did

- Deleted `.taskmaster/` entirely.
- Removed Task Master references from docs, README, and `.gitignore`.
- Added manual checklist: `docs/09-TASKS.md`.

### Decision

- **No Task Master.** Planning and progress tracking stay in `docs/` only.

### Next

- On approval ? Phase 1 scaffolding.

---

## 2026-09-04 ? Continuing build (user: Docker restarted, no pause)

### Intent

Finish Phase 2 migrate/seed, then proceed through Phases 3+ without waiting for go-ahead.

### Status

In progress.

---

## 2026-09-04 ? Phases 2?9 + frontend digest (continued autonomously)

### What we did

- Fixed Postgres host port clash (local `postgres.exe` vs Docker) ? **55432**.
- Migrated + seeded DB; demo user `demo@example.com` / `DemoPass123!`.
- Auth (JWT, Argon2id), watchlist CRUD, instrument search, IDOR-safe 404s.
- Analytics: price anomaly, RVOL, market/sector context, CUSUM.
- Scoring: fusion, significance, confidence, novelty, attention.
- Replay fixtures + `python -m app.demo_pipeline` (HDFC HIGH, Reliance suppressed, TCS notable).
- Digest + mark-seen APIs; template explanations.
- Frontend WatchlistApp with attention cards, evidence panel, mark-seen.
- Tests: **17 passed** (unit + security).

### Verified

- Digest: HDFC `HIGH_ATTENTION` 0.8; mark-seen removes HDFC; TCS remains.

### Still open

- WebSocket live fan-out (Phase 10)
- SECURITY.md / full hardening docs (Phase 13)
- Full Docker compose of api+web in one shot

### Next

- Phase 10 WebSocket; polish SECURITY/DEMO docs.

---

## 2026-09-04 ? Phase 1 complete: repo & infra skeleton

### What we did

- Scaffolded FastAPI backend (`/health`, `/ready`, CORS, central config, package tree).
- Scaffolded Next.js 15 + Tailwind frontend with landing page + API status chip.
- Added Docker Compose (postgres, redis, api, worker stub, web), Dockerfiles, Makefile, `.env.example`.
- Added backend health unit tests (3 passed).
- Verified `uvicorn` `/health` ? 200, mode=`replay`.
- Verified `npm run build` succeeds.
- Docker Compose not fully verified ? Docker Desktop engine was not running.

### Files created (high level)

- `backend/app/**`, `backend/Dockerfile`, `backend/requirements*.txt`, `backend/tests/unit/test_health.py`
- `frontend/**` (Next.js app)
- `docker-compose.yml`, `Makefile`, `.env.example`, `.env`

### Decisions

- Manual Next.js scaffold (create-next-app hung on interactive prompt).
- `/ready` honestly reports DB/Redis as `pending` until Phase 2 wiring.
- Worker container is an idle stub until Phase 5+.

### Tests run

- `pytest tests/unit/test_health.py` ? 3 passed
- `npm run build` ? success
- Live `GET /health` ? ok

### Next

- Phase 2: SQLAlchemy models, Alembic migration, seed instruments.
- When Docker Desktop is on: `docker compose up --build` for full stack check.

---

## 2026-09-04 ? Phase 2: database models + migration + seed (code)

### What we did

- Added SQLAlchemy models for users, instruments, watchlists, items, price_points, market_events, event_evidence, snapshots.
- Added Alembic async env + `0001_initial` migration.
- Added Argon2 hashing helper and `python -m app.seed` with stable demo UUIDs (HDFC/Reliance/TCS/INFY/ICICI + Nifty indices).
- Wired `/ready` to probe Postgres + Redis.
- Remapped Compose Postgres host port to **5433** (local 5432 was already occupied).
- Settings now loads repo-root `.env`.

### Blockers

- Docker Desktop engine dropped mid-session; host migrate/seed not fully verified yet.
- Earlier password errors traced to port collision with another Postgres on 5432.

### Next

- With Docker healthy: `docker compose up -d postgres redis` ? `alembic upgrade head` ? `python -m app.seed`.
- Then Phase 3: auth APIs.

---

## 2026-09-04 ? Ship rest: live path, frontend polish, security + docs

### What we did

- Wired WebSocket to Redis pub/sub fan-out with degraded ? polling message; client useWatchlistSync fallback (8s / 60s).
- Added `market_worker` and pointed Compose worker at it.
- Frontend: login form + localStorage token, connection chip, `StaleDataBadge`, `DataConflictBadge`, sign-out.
- Digest exposes `data_age_seconds` / `data_conflict`; explanations via optional LLM stub (templates by default).
- Hardened response headers (frame deny, permissions-policy, HSTS in production).
- Docs: `SECURITY.md`, `API.md`, `DEMO.md`; updated ARCHITECTURE live path, INDEX, README, tasks 13?15.
- Tests: security headers + digest auth, escalation unit test.

### Decision

- Tier 3 stretch (OLS / Isolation Forest / FinBERT) skipped for demo scope.
- LLM remains feature-flagged and never scores significance.

### Next

- Judge acceptance walk per `docs/DEMO.md`.

## 2026-09-05 ù Tier 1+2 completion wave

### What we did

- Plan: `docs/plans/tier12-completion.md`
- Shared `services/pipeline.py`; continuous `market_worker` ingest/detect/score/notify
- Live-sim provider, CA adjuster, filings catalog; expanded replay (SBIN/WIPRO/LT)
- Migration `0002`: user sensitivity + notifications table/API
- Settings API; grounded LLM paraphraser; peer snapshots on digest cards
- Frontend: register, watchlist CRUD, price rows, alerts bell, sensitivity, peers

### Tests

- `pytest` ? 22 passed after migration fix

### Deferred

- Native mobile / FCM / Chrome extension / Tier 3 ML

## 2026-09-05 ù Multi-tab demo UX + RAG + live-sim + notes

### What we did

- Plan: `docs/plans/demo-ux-rag-livesim.md`; LLM guide: `docs/LLM.md`
- Multi-tab UI: Market / Watchlist / Attention / Alerts / Settings
- Live-sim tape API `GET /api/v1/market/tape` + `WS /ws/tape` with flash updates
- Watchlist item `note` (migration 0003) + note-on-add UI
- RAG over `data/filings/docs` + optional DuckDuckGo web retrieval
- Real free-tier LLM clients: Groq (primary) / Gemini (fallback)
- Tests: 23 passed including RAG unit test

### LLM for user

- Prefer Groq `llama-3.1-8b-instant` ù set `ENABLE_LLM=true` + `LLM_API_KEY`

### Still deferred

- Native mobile / FCM / Chrome extension / Tier 3 ML / licensed live exchange feed

## 2026-09-05 ù Provenance, ignored strip, eval, notes-in-explain

### What we did

- Digest returns `retrieval` chips + `ignored` list with reasons
- Attention UI: retrieval provenance, user note, IgnoredStrip
- Expanded filings corpus (TCS/RELIANCE/INFY/ICICI/WIPRO context docs)
- `python -m app.eval` golden scenarios (5/5)
- Notes only affect explanation text, never significance
- DEMO.md 90-second judge script

### Verify

- `python -m app.eval` ? 5/5
- pytest green

## 2026-09-05 ù Mark-seen / reset / live-sim attention fixes

### What we did

- Novelty: same severity after mark-seen stays at 0 even if event version ticks
- Escalation: version++ only when severity rises (not every evidence refresh)
- Live-sim volume: noise around seed baseline (no compound fake RVOL)
- Engine sync: price ingest every ~8s; full rescore every ~64s
- RAG: symbol-scoped retrieval only
- Clearer UI errors when Mark seen / Reset fail (Chrome extensions)

### Verify

- `python -m app.demo_pipeline` then hard-refresh Attention
- Mark seen ? Ignored strip; Reset demo novelty ? cards return
- If Failed to fetch from chrome-extension://, use Incognito

---

## 2026-09-05 ù Competition packaging

### Decision

- Judge demo stays on **`MARKET_DATA_MODE=replay`** (not Yahoo).
- Yahoo provider kept as optional flag only.
- Feedback loop shipped for PRD label gap.

### Docs

- Rewrote README + DEMO + 00-INDEX for Groww CODE judges.
- Canvas: `groww-code-competition` brief for pitch/map.

## 2026-09-05 ù Continuous S + trust polish + docs/test sweep

### What we did
- Continuous Significance inside severity bands; realistic MAD baseline + z cap
- Template comma fix; digest headline; confidence_breakdown; DEMO conflict/skip-cal knobs
- Ignored strip leads Attention UI; Info/README/PROJECT-COMPLETE/API/EDGE-CASES/DEMO/CHANGELOG updated
- Full pytest + eval + sanity script for breakage

### Verify
- `python -m pytest -q`
- `python -m app.eval` ? 5/5
- Hard-refresh Attention: different S on same-tier cards; TCS conflict line; no stray comma

---

## 2026-09-07 ó Submission polish

### What we did
- Aligned docs to `DEMO_CONFLICT_SYMBOL=TCS`; cleaned `.env.example` / CHANGELOG encoding
- Removed unused `@tanstack/react-query`; bumped Next.js to 15.5.25
- Full verify: pytest 28, eval 5/5, lint, tsc, production build

### Decision
- Do not force Next 16 for remaining nested PostCSS advisories (breaking); demo stays on Next 15.5.x

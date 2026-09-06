# Plan — Complete Tier 1 + Tier 2 (excl. mobile / Chrome extension)

**Date:** 2026-09-05  
**Goal:** Close all remaining Tier 1 and Tier 2 gaps from `docs/03-FEATURES.md`, plus related UI/data/worker paths. Out of scope: native mobile, Chrome extension, Tier 3 ML stretch.

---

## Current state (summary)

| Area | Status |
|------|--------|
| Auth / watchlist APIs / digest / scoring / replay demo / WS | Done |
| Continuous detect→score worker | Heartbeat only |
| Live provider | Missing (`live` mode unused) |
| CA/split adjust | Missing |
| Register + watchlist CRUD UI + price rows | Missing / thin |
| Notifications (in-app HIGH alerts) | Missing |
| Sensitivity + peer UI | Missing |
| Real LLM | Stub → templates only |
| Filings/CA feed | Demo-hardcoded HDFC only |
| Replay for SBIN/WIPRO/LT | Missing |

---

## Architecture decisions

1. **“Live” for this product = MockLive stream** when no broker keys: `ingestion/live.py` wraps mock/replay ticks on a timer. Real broker adapter stays behind the same interface.
2. **Worker becomes the brain:** every N seconds: pull latest prices for all watchlisted instruments → normalize → adjust CA → run detectors → upsert events → if HIGH+novel, write `Notification` + Redis publish.
3. **Notifications = in-app + WS**, not FCM (no mobile). Table `notifications` + `GET /notifications` + badge in UI. Satisfies “background compute + alert without opening digest first.”
4. **LLM:** when `ENABLE_LLM=true`, use a local grounded paraphraser (evidence-only rewrite). No external API keys required for demo; same interface as a future OpenAI adapter.
5. **Sensitivity:** `users.sensitivity` enum LOW|MEDIUM|HIGH scales fusion thresholds / attention floor for that user.
6. **Peer view:** UI panel comparing stock vs sector peers from same-sector instruments + residuals already in evidence.

---

## Build waves

### Wave A — Data & ingestion foundation
1. Expand `data/replay/demo_session.json` for SBIN, WIPRO, LT (+ denser ticks for multi-horizon where feasible).
2. Add `data/filings/demo_filings.json` (instrument_id → filing metadata).
3. Add `ingestion/corporate_actions.py` — apply simple split/bonus adjust to series before detectors.
4. Add `ingestion/live.py` — MockLiveProvider cycling ticks; wire `market_data_mode` factory.
5. Add `ingestion/filings.py` — load demo filings into information_evidence.
6. Generalize `demo_pipeline` / share `services/pipeline.py` used by worker + CLI.

### Wave B — Continuous worker + notifications
1. Refactor detection into `services/pipeline.py` (`run_tick_cycle(session)`).
2. Upgrade `workers/market_worker.py` to call pipeline + publish.
3. Migration `0002_notifications_sensitivity`:  
   - `users.sensitivity`  
   - `notifications(id, user_id, watchlist_id, event_id, title, body, severity, read_at, created_at)`
4. API: `GET/POST /notifications`, mark-read; create on HIGH upsert for watchlist owners.
5. WS payload type `notification`.

### Wave C — Settings, sensitivity, LLM, peers (Tier 2)
1. `GET/PATCH /api/v1/me/settings` (sensitivity).
2. Digest/scoring applies user sensitivity multipliers.
3. `explanation/llm.py` — grounded paraphraser when flag on.
4. Peer comparison endpoint or digest field: peers in same sector with returns.

### Wave D — Frontend Tier 1+2 UI
1. Register form + toggle on login.
2. Watchlist switcher: create / rename / delete.
3. `WatchlistView` price rows (last price, change, age, attention tier if any).
4. Notifications bell + panel.
5. Sensitivity slider in header/settings.
6. Peer comparison section on AttentionCard / side panel.
7. API client methods for all new endpoints.

### Wave E — Harden & docs
1. Tests: pipeline unit, notifications authz, settings, CA adjust.
2. Update DEMO.md, API.md, FEATURES checkboxes, changelog, tasks, development log.
3. Re-run pytest + smoke digest/login.

---

## Critical files

| Path | Change |
|------|--------|
| `backend/app/services/pipeline.py` | **New** shared detect/score cycle |
| `backend/app/workers/market_worker.py` | Real cycle |
| `backend/app/ingestion/{live,filings,corporate_actions}.py` | **New** |
| `backend/app/db/models/{user,notification}.py` | Sensitivity + notifications |
| `backend/alembic/versions/0002_*.py` | Migration |
| `backend/app/api/{notifications,settings}.py` | **New** |
| `backend/app/explanation/llm.py` | Grounded paraphraser |
| `frontend/src/components/*` | Register, CRUD, prices, notif, sensitivity, peers |
| `data/replay/demo_session.json` | Expand |
| `data/filings/demo_filings.json` | **New** |

---

## Verification

1. `alembic upgrade head` → seed → worker running → events appear without manual `demo_pipeline`.
2. Register new user → create watchlist → add SBIN → see price row after tick.
3. HIGH event → notification row + WS `notification` message.
4. Sensitivity HIGH vs LOW changes digest membership/thresholds.
5. `ENABLE_LLM=true` changes explanation wording but not scores.
6. Peer panel shows same-sector residuals/returns.
7. `pytest` green; UI smoke on localhost.

---

## Explicitly still deferred

- Native mobile / FCM push  
- Chrome extension  
- Tier 3 (OLS, Isolation Forest, FinBERT)  
- Real broker WebSocket credentials  

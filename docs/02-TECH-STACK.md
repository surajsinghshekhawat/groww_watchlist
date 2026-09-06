# 02 — Tech Stack & Tools

---

## Frontend

| Layer | Choice | Notes |
|-------|--------|-------|
| Framework | **Next.js** (App Router) | SSR/client hybrid for watchlist UI |
| Language | **TypeScript** | Strict typing at API boundaries |
| UI | **React** + **Tailwind CSS** + **shadcn/ui** | Clean financial UI, accessible |
| Charts | **Lightweight Charts** (or equivalent) | Price context, not indicator spam |
| Server state | **TanStack Query** | Watchlist / digest fetch + cache |
| Live | Native **WebSocket** client | With reconnect + polling fallback |
| State | React state + Query — **no Redux** unless forced | Keep simple |

---

## Backend

| Layer | Choice | Notes |
|-------|--------|-------|
| Runtime | **Python 3.11+** | Analytics-friendly |
| API | **FastAPI** + **Uvicorn** | Async REST + WebSockets |
| Validation | **Pydantic** / **Pydantic Settings** | Schemas + env config |
| ORM | **SQLAlchemy 2.x** | Async |
| Migrations | **Alembic** | Never hand-edit prod schema |
| DB driver | Async PostgreSQL (`asyncpg`) | |
| Cache / pub-sub | **Redis** client | Hot state, streams, rate limits, fan-out |

Backend must stay **modular** — no monolith `main.py`.

---

## Analytics

| Library | Role |
|---------|------|
| **NumPy** | Core numeric |
| **Pandas** or **Polars** | Series / windows |
| **SciPy** | Stats helpers as needed |
| **scikit-learn** | Optional Isolation Forest only |
| **statsmodels** | Optional rolling OLS only |

**Core path must not depend on ML.**

---

## Persistence

| Store | Role |
|-------|------|
| **PostgreSQL** | Source of truth: users, watchlists, events, snapshots, prices |
| **Redis** | Hot market state, feature cache, streams, pub/sub, rate limiting |

If Redis fails: durable CRUD continues; live updates degrade.

---

## Infrastructure

| Tool | Role |
|------|------|
| **Docker** + **Docker Compose** | Local multi-service run |
| **Makefile** | Common commands (`up`, `test`, `seed`, `migrate`) |
| **`.env` / `.env.example`** | Secrets via env only |
| Separate containers | frontend / backend / worker / postgres / redis |

No Kubernetes. No Kafka unless explicitly requested later.

---

## Development & quality tools

| Tool | Purpose |
|------|---------|
| **pytest** | Backend unit / integration / security tests |
| **Vitest** / Playwright (as needed) | Frontend tests |
| **Manual checklist** | `docs/09-TASKS.md` — no Task Master |
| **Cursor** | Primary IDE / agent coding |
| **Git** | Version control (commits only when asked) |
| **gh** | PRs when requested |
| Structured logging | Request IDs; never log secrets |

---

## Market data strategy

Abstract behind `MarketDataProvider`:

1. `ReplayMarketDataProvider` — **default for demo** (deterministic)  
2. `MockMarketDataProvider` — unit tests  
3. `LiveMarketDataProvider` — optional when credentials exist  

Core demo must work **without** live market API, news API, or LLM API.

---

## Optional / feature-flagged

| Flag | Default |
|------|---------|
| `ENABLE_CUSUM` | true for Tier 2 path once Tier 1 solid |
| `ENABLE_LLM` | false until keyed |
| `ENABLE_NEWS` | false |
| `ENABLE_ROLLING_OLS` | false |
| `ENABLE_ISOLATION_FOREST` | false |
| `ENABLE_FINBERT` | false |

---

## Documentation & planning tools (this phase)

| Artifact | Location |
|----------|----------|
| Product / stack / plan docs | `docs/` |
| Step-by-step build diary | `docs/07-DEVELOPMENT-LOG.md` |
| Changelog | `docs/08-CHANGELOG.md` |
| Phase plans | `docs/plans/` |
| Manual task checklist | `docs/09-TASKS.md` |

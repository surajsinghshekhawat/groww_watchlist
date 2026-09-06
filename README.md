# Smart Market Watchlist

**Groww CODE 2026** — state-aware **attention ranking** for equity watchlists.

> Groww already shows prices. We decide **what deserves attention** after your last check — the smallest novel, trustworthy set — with evidence, and we show what we *refused* to surface. We do **not** predict prices or issue buy/sell advice.

```
ATTENTION = SIGNIFICANCE × NOVELTY × CONFIDENCE
```

| Factor | Meaning |
|--------|---------|
| **Significance** | Unusual vs history + context; **continuous inside** each severity band (labels stay discrete) |
| **Novelty** | New to *this user* at *this event state* (mark-seen → collapses until escalation) |
| **Confidence** | Trust in the data (freshness / agreement) — cards show a one-line *why* |

**LLM never sets the score** — it may only narrate verified evidence (optional).

---

## For judges (start here)

| Doc | Why |
|-----|-----|
| **[docs/DEMO.md](./docs/DEMO.md)** | Live walkthrough script (~2–6 min) |
| **[docs/PROJECT-COMPLETE.md](./docs/PROJECT-COMPLETE.md)** | Full deep dive — math, architecture, features, strategy |
| **[docs/01-PRODUCT.md](./docs/01-PRODUCT.md)** | Problem, non-goals, scoring rules |
| **[docs/03-FEATURES.md](./docs/03-FEATURES.md)** | What shipped (Tier 1–2) |
| **[docs/API.md](./docs/API.md)** | HTTP + WebSocket |
| **[docs/SECURITY.md](./docs/SECURITY.md)** | Authz / IDOR / headers |

**Demo login:** `demo@example.com` / `DemoPass123!`  
**Data mode for the pitch:** `MARKET_DATA_MODE=replay` (stable HDFC story).  
**Eval:** `cd backend && python -m app.eval` → expect **5/5**.

### Pitch in 20 seconds

1. Watchlist = input (Groww-like curation).  
2. Attention = product (`S · N · C` cards + **What we ignored**).  
3. HDFC → High (filing + residual + volume); Reliance → suppressed (market-aligned).  
4. Continuous \(S\) differentiates same-tier cards; INFY can show `DATA_CONFLICT` via demo knob.  
5. Mark seen → novelty memory. Feedback / push / NLP are supporting, not the thesis.

---

## What’s in the app

| Tab | Purpose |
|-----|---------|
| **Market** | Live-sim tape (same ticks sync into the engine) |
| **Watchlist** | CRUD lists, add/remove names, notes, NLP “describe a watchlist” |
| **Attention** | Ranked digest + **headline**, **ignored-first**, evidence, peers, RAG, mark-seen, feedback, confidence why-line |
| **Alerts** | Attention-gated in-app notifications |
| **Settings** | Sensitivity + Web Push |
| **Info** | Honest product brief for judges |

---

## Stack

| Layer | Choice |
|-------|--------|
| Frontend | Next.js, React, TypeScript, Tailwind |
| Backend | FastAPI, SQLAlchemy 2, Alembic, Pydantic |
| Data | PostgreSQL (source of truth), Redis (pubsub / cache) |
| Analytics | NumPy / Pandas / SciPy (interpretable detectors) |
| Infra | Docker Compose (Postgres + Redis) |

Details: [docs/02-TECH-STACK.md](./docs/02-TECH-STACK.md) · Architecture: [docs/05-ARCHITECTURE.md](./docs/05-ARCHITECTURE.md)

---

## Quick start

### Prerequisites

- Docker Desktop (Postgres + Redis), **or** local Postgres/Redis matching `.env`
- Python 3.11+, Node 20+

### Boot (recommended)

```powershell
cd "path\to\groww - watchlist"
copy .env.example .env   # if needed; keep MARKET_DATA_MODE=replay

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
- API health: http://localhost:8000/health  
- OpenAPI: http://localhost:8000/docs  

Use **Incognito** if Mark seen fails (`Failed to fetch` from browser extensions).

### Tests

```powershell
cd backend
python -m pytest -q
```

---

## Data modes (honesty)

| Mode | Use |
|------|-----|
| **`replay`** (default) | Judge demo — seeded session + live-sim tape |
| `yahoo` | Optional delayed NSE quotes via [yfinance](https://github.com/ranaroussi/yfinance) — **not** the pitch path |
| `live` / `mock` | Live-sim / test providers |

Filings/RAG use a **local demo corpus** (`data/filings/`). Architecture is provider-shaped for a real feed later.

Optional LLM: [docs/LLM.md](./docs/LLM.md). Push: [docs/PUSH.md](./docs/PUSH.md).

---

## Non-goals

- Price prediction / “will rise” models  
- Trading bot / buy-sell recommendations  
- Full RSI/MACD dashboard  
- Ungrounded LLM “analyst” that invents numbers or sets significance  

---

## Docs map

Full index: **[docs/00-INDEX.md](./docs/00-INDEX.md)**

| Path | Purpose |
|------|---------|
| `docs/DEMO.md` | Judge script |
| `docs/09-TASKS.md` | Phase checklist |
| `docs/07-DEVELOPMENT-LOG.md` | Build diary |
| `docs/08-CHANGELOG.md` | Notable changes |
| `data/replay`, `data/filings` | Demo fixtures |

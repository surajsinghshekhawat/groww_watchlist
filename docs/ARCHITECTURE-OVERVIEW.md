# Architecture overview

**Smart Market Watchlist** — Groww CODE 2026  
One-page view for judges. Deep dive: [05-ARCHITECTURE.md](./05-ARCHITECTURE.md) · Decisions: [DECISIONS.md](./DECISIONS.md)

![System architecture](./assets/architecture-overview.png)

---

## 1. Deployed shape (what is live)

```mermaid
flowchart LR
  User[Judge / user browser]
  Web["Next.js UI<br/>Vercel"]
  API["FastAPI API + WS<br/>Railway"]
  PG[(PostgreSQL)]
  RD[(Redis)]
  Worker["market_worker<br/>optional"]

  User --> Web
  Web -->|"HTTPS REST"| API
  Web -->|"WSS / polling fallback"| API
  API --> PG
  API --> RD
  Worker --> PG
  Worker --> RD
```

| Piece | Role |
|-------|------|
| **Vercel** | Static/SSR web UI — [live app](https://groww-watchlist-xi.vercel.app/) |
| **Railway API** | Auth, watchlists, digest, notifications, WebSocket, live-sim tape |
| **Postgres** | Source of truth — users, lists, prices, events, evidence, snapshots |
| **Redis** | Pub/sub fan-out for live updates (not durable truth) |

---

## 2. Attention engine (product core)

```mermaid
flowchart TB
  MD["Market data<br/>replay · live-sim · yahoo"]
  Norm["Normalize<br/>instrument_id · CA adjust · freshness"]
  Det["Detectors<br/>MAD anomaly · RVOL · market/sector residual · CUSUM"]
  Fuse["Evidence fusion<br/>market · context · persistence · information"]
  S["Significance S<br/>bands + continuous inside"]
  C["Confidence C<br/>freshness × agreement"]
  N["Novelty N<br/>per-user event state"]
  A["Attention A = S × N × C"]
  Out["Digest top-K + ignored strip<br/>template / optional LLM narrate"]

  MD --> Norm --> Det --> Fuse
  Fuse --> S
  Fuse --> C
  Fuse --> N
  S --> A
  N --> A
  C --> A
  A --> Out
```

**Rule:** the LLM may narrate verified evidence; it **never** assigns \(S\), \(N\), \(C\), or \(A\).

---

## 3. Request path (Attention tab)

```mermaid
sequenceDiagram
  participant UI as Next.js
  participant API as FastAPI
  participant DB as Postgres
  participant R as Redis

  UI->>API: GET /watchlists/{id}/digest (JWT)
  API->>DB: load watchlist, prices, events, snapshots
  API->>API: score / rank / ignore reasons
  API-->>UI: cards + headline + ignored[]

  UI->>API: WS /ws/watchlists/{id}?token=
  API->>R: subscribe watchlist:live:{id}
  Note over UI,API: on WS failure → poll digest 8s / 60s
```

---

## 4. Persistence split

| Concern | Store |
|---------|--------|
| Users, watchlists, items, events, evidence, snapshots, price history | **PostgreSQL** |
| Live tape fan-out, pub/sub, hot ephemeral streams | **Redis** |

Identity key is always `instrument_id` (UUID) — never ticker-as-PK.

---

## 5. Repo map (where code lives)

| Path | Responsibility |
|------|----------------|
| `frontend/src/components/` | Market, Watchlist, Attention, Alerts, Settings |
| `backend/app/api/` | REST + WebSocket routes |
| `backend/app/ingestion/` | Providers (replay / live / yahoo), normalize, filings |
| `backend/app/analytics/` | MAD, RVOL, residuals, CUSUM |
| `backend/app/scoring/` | significance, novelty, confidence, attention, fusion |
| `backend/app/services/` | digest, pipeline, auth, notifications, push |
| `backend/app/workers/` | background ingest → score → notify |
| `backend/data/` · `data/` | Replay session + demo filings (Docker ships `backend/data`) |

---

## 6. Data honesty

| Mode | Meaning |
|------|---------|
| **`replay` (default)** | Seeded demo session + in-process live-sim tape — **judge / production demo path** |
| `yahoo` | Optional delayed quotes — not the pitch |
| Filings / RAG | Local demo corpus — architecture ready for a real feed later |

---

## Related docs

- [05-ARCHITECTURE.md](./05-ARCHITECTURE.md) — locked design notes  
- [API.md](./API.md) — endpoints  
- [SECURITY.md](./SECURITY.md) — authz / headers  
- [DECISIONS.md](./DECISIONS.md) — what we deferred or rejected  

# 05 — Architecture (Overview)

Detailed design expands as we implement. This is the locked high-level shape.

---

## System diagram

```
                         MARKET DATA (live | replay | mock)
                              |
                              v
                 +------------------------+
                 | NORMALIZATION          |
                 | instrument_id, CA adj, |
                 | source, freshness      |
                 +-----------+------------+
                             |
          +------------------+------------------+
          v                  v                  v
     PRICE ANOMALY      RVOL (TOD)      MARKET/SECTOR CTX
          |                  |                  |
          +------------------+------------------+
                             v
                    CUSUM (corroborate only)
                             v
                      CANDIDATE EVENT
                             v
                 FILING / CA / EARNINGS
                             v
                     EVIDENCE FUSION
                             v
                       SIGNIFICANCE
                  +----------+----------+
                  v                     v
              CONFIDENCE            USER SNAPSHOT
                                        v
                                      NOVELTY
                  +----------+----------+
                             v
                         ATTENTION → TOP-K
                             v
                      EXPLAIN (template | LLM)
                             v
                 WS / REST / notifications → CLIENT
```

---

## Persistence split

| Concern | Store |
|---------|--------|
| Users, watchlists, items, events, evidence, snapshots, price history | **PostgreSQL** |
| Hot ticks, feature cache, streams, pub/sub, rate limits | **Redis** |

Redis is never the durable source of truth for watchlists/events.

---

## Identity

- Permanent key: `instrument_id` (UUID)  
- `symbol` is mutable display metadata  
- `company_id` links dual listings  
- Watchlist items reference `instrument_id` only  

---

## Event model

`MarketEvent` is first-class and versioned:

- Types: PRICE_ANOMALY, VOLUME_ANOMALY, CONTEXT_DIVERGENCE, CHANGE_POINT, CORPORATE_ACTION, FILING, EARNINGS  
- Severity: LOW | NOTABLE | WORTH_WATCHING | HIGH  
- Status: OPEN → ESCALATED → RESOLVED  
- New evidence updates the same event (dedupe), increments `version`  

---

## Live path (implemented)

```
market_worker / demo_pipeline
        |
        v
  Postgres (events) ──► digest REST
        |
        +──► Redis pub/sub channel watchlist:live:{id}
                    |
                    v
           WS /ws/watchlists/{id}?token=
                    |
         on failure / degraded
                    v
           client polling digest (8s active / 60s background)
```

Worker entry: `python -m app.workers.market_worker`.

---

## Scoring contracts

Documented in code under `backend/app/scoring/` and config — no magic numbers in detectors.

Evidence fusion groups:

1. **Market** — price anomaly OR RVOL  
2. **Context** — market/sector residual  
3. **Persistence** — CUSUM  
4. **Information** — filing/CA/earnings (can override to HIGH)  

---

## API surface (auth-derived ownership)

```
POST/GET auth routes
GET/POST/PATCH/DELETE /watchlists
POST/DELETE /watchlists/{id}/instruments
GET /watchlists/{id}/digest
POST /watchlists/{id}/mark-seen
GET /instruments/search
WS  /ws/watchlists/{id}
GET /health , /ready
```

Never authorize by trusting a client-supplied `userId` path param.

---

## Scaling pattern

One upstream feed per instrument → Redis → fan-out to subscribers.  
Never N_users × N_stocks polling of upstream.

Active UI: frequent updates. Background: slower. Closed: HIGH-only push policy (Tier 1 may simulate via UI).

---

## Failure isolation

| Failure | Behavior |
|---------|----------|
| LLM / retrieval | Template explanation |
| Redis | CRUD from Postgres; live degrades |
| One detector | Others continue; confidence/evidence reflect gaps |
| Stale/conflict data | Confidence ↓; suppress false HIGH |

---

## Project layout (target)

See Implementation Plan and PRD §5. Top level:

```
smart-market-watchlist/
  backend/app/{api,core,db,schemas,repositories,ingestion,
               analytics,events,scoring,explanation,sync,workers,services}
  frontend/{app,components,hooks,lib}
  data/{seed,replay}
  docs/
  docker-compose.yml
```

---

## Why not ML-first?

No reliable public labels for “meaningful.” Interpretable evidence is the correct v1 engineering choice. Optional ML later = candidate generator only, never sole HIGH trigger.

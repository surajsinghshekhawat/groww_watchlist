# API reference

Base URL (local): `http://127.0.0.1:8000`  
Versioned prefix: `/api/v1`  
OpenAPI: `/docs` (disabled when `APP_ENV=production`)

Errors use a consistent envelope:

```json
{
  "error": {
    "code": "WATCHLIST_NOT_FOUND",
    "message": "Watchlist not found",
    "request_id": "…"
  }
}
```

## Health

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/health` | no | Liveness |
| GET | `/ready` | no | Postgres + Redis probes |

## Auth

| Method | Path | Body |
|--------|------|------|
| POST | `/api/v1/auth/register` | `{ email, password, display_name }` |
| POST | `/api/v1/auth/login` | `{ email, password }` |

Response includes `user` + `token.access_token`.

Demo user (after seed): `demo@example.com` / `DemoPass123!`

## Instruments

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/v1/instruments/search?q=` | yes |

## Watchlists

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/api/v1/watchlists` | yes | Owned lists |
| POST | `/api/v1/watchlists` | yes | Create |
| GET | `/api/v1/watchlists/{id}` | yes | 404 if not owned |
| PATCH | `/api/v1/watchlists/{id}` | yes | Version conflict → 409 |
| DELETE | `/api/v1/watchlists/{id}` | yes | |
| PUT | `/api/v1/watchlists/{id}/items` | yes | Replace instrument set |

## Digest

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/v1/watchlists/{id}/digest?top_k=` | yes |
| POST | `/api/v1/watchlists/{id}/mark-seen` | yes |
| POST | `/api/v1/watchlists/{id}/reset-seen` | yes |
| POST | `/api/v1/watchlists/{id}/touch-checked` | yes |
| GET | `/api/v1/watchlists/{id}/prices` | yes |
| POST | `/api/v1/events/{event_id}/feedback` | yes — body `{ "label": "useful\|noise\|already_knew", "watchlist_id": "…" }` |

Digest items may include `user_feedback`, `user_note`, `retrieval` chips.

## NLP watchlist

| Method | Path | Auth |
|--------|------|------|
| POST | `/api/v1/watchlists/from-intent/preview` | yes |
| POST | `/api/v1/watchlists/from-intent/confirm` | yes |

## Notifications & settings

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/v1/notifications?unread_only=` | yes |
| POST | `/api/v1/notifications/mark-read` | yes |
| GET | `/api/v1/me/settings` | yes |
| PATCH | `/api/v1/me/settings` | yes — body `{ "sensitivity": "LOW\|MEDIUM\|HIGH" }` |

## Live channel

Digest item fields include `attention_score`, `significance`, `novelty`, `confidence`, `confidence_breakdown`, `tier`, `explanation`, `evidence`, `data_conflict`, `data_age_seconds`, `user_note`, `user_feedback`.

Digest `summary` also includes `headline`, `ignored_count`, `hidden_high`, `empty_hint`.

Env knobs relevant to digest talk-track: `DEMO_CONFLICT_SYMBOL`, `DEMO_SKIP_CALIBRATION`, `MAX_PRICE_ANOMALY_Z`.

Mark-seen body:

```json
{
  "items": [
    {
      "event_id": "…",
      "severity_seen": "HIGH",
      "event_version": 1
    }
  ]
}
```

## Live channel

| Proto | Path | Auth |
|-------|------|------|
| WebSocket | `/ws/watchlists/{id}?token=` | JWT query param |

Messages: `subscribed`, `heartbeat`, `pong` (reply to client `ping`), `event` (Redis fan-out), `degraded` (poll fallback).

## Modes

`MARKET_DATA_MODE` = `replay` | `mock` | `live` | `yahoo` (see config / `.env`). Judge default: **`replay`**.

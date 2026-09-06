# Phase 2 Plan — Database foundation

**Status:** Code complete · migrate/seed pending stable Docker  
**Date:** 2026-09-04

## Goal

SQLAlchemy models, Alembic initial migration, seed demo instruments/user/watchlist.

## Deliverables

- [x] Models: users, instruments, watchlists, items, price_points, market_events, evidence, snapshots
- [x] Alembic `0001_initial` migration
- [x] Async session + `get_db_session`
- [x] Argon2 password helper
- [x] `python -m app.seed` (demo user + 5 stocks + indices + snapshots)
- [x] `/ready` checks DB + Redis
- [ ] `alembic upgrade head` verified (blocked: Docker Desktop engine flaky / port 5432 conflict)
- [ ] Seed applied to live DB

## Notes

- Host Postgres mapped to **55432** to avoid conflict with an existing local Postgres on 5432.
- Settings loads repo-root `.env`.
- Demo login (dev only): `demo@example.com` / `DemoPass123!`

## When Docker is up

```bash
docker compose up -d postgres redis
cd backend
alembic upgrade head
python -m app.seed
```

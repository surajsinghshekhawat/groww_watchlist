# 08 - Changelog

All notable changes to this project are documented here.

Format inspired by [Keep a Changelog](https://keepachangelog.com/).  
Versions are informal until first demo tag.

---

## [2026-09-07] - Submission polish

### Changed
- README / docs: conflict demo symbol aligned to **TCS** (`DEMO_CONFLICT_SYMBOL`).
- `.env.example` comment encoding cleaned; plan notes match demo email + Postgres port **55432**.
- Removed unused `@tanstack/react-query` dependency.
- Next.js bumped for known advisory patches (see `package.json`).

---

## [2026-09-05] - Continuous S, z sanity, digest trust polish

### Added
- Continuous Significance inside severity bands (`significance_continuous`).
- Digest `summary.headline` + item `confidence_breakdown`.
- Demo knobs: `DEMO_CONFLICT_SYMBOL`, `DEMO_SKIP_CALIBRATION`, `MAX_PRICE_ANOMALY_Z`.
- Unit tests: templates, continuous S, conflict breakdown, 1% vs 4% z differentiation.

### Changed
- MAD baseline uses realistic ~1% equity noise (not near-flat +/-0.2% series).
- Attention UI: ignored strip first; Info tab documents continuous S / conflict demo.
- Docs: README, DEMO, PROJECT-COMPLETE, API, EDGE-CASES, product/features.

### Fixed
- Template stray comma ("TCS, is up...").
- Flat S causing identical Attention for same-tier cards.

---

## [2026-09-05] - Competition packaging + feedback + Yahoo provider

### Added

- Attention feedback: `useful` / `noise` / `already_knew` (`event_feedback`, `POST /events/{id}/feedback`).
- Optional `MARKET_DATA_MODE=yahoo` provider (yfinance + curl_cffi); **judge default remains `replay`**.
- Competition-facing README, DEMO, docs index refresh.
- Edge-case Wave 1-2 fixes (calibration gate, notify-once, digest edges, etc.).

### Changed

- Default pitch path locked to **replay** for stable HDFC / Reliance story.
- Info tab + product docs: honest framing for Groww CODE judges.

---

## [Unreleased]

### Added

- Phase 1-14 stack: FastAPI, Next.js, Postgres/Redis, scoring, digest, WebSocket, demo replay.
- Redis-backed WebSocket fan-out + market worker heartbeats.
- Frontend login, reconnect/polling sync, stale/conflict badges.
- `docs/SECURITY.md`, `docs/API.md`, `docs/DEMO.md`.
- Security header + digest tests; escalation unit tests.

### Changed

- Digest payload includes `data_age_seconds` / `data_conflict`.
- Compose worker runs `python -m app.workers.market_worker`.
- Compose Postgres host port **55432** (avoid local Windows Postgres clash).
- Tasks 13-14 marked done; Tier 3 skipped.

### Security

- Extra API headers (`X-Frame-Options`, `Permissions-Policy`, production HSTS).
- Argon2id auth, IDOR returns 404, rate limits, JWT ownership checks.

### Removed

- `.taskmaster/` directory and all Task Master workflow references.

---

## [2026-09-05] - Attention stability (mark-seen / live-sim)

### Fixed
- Mark-seen not sticking (version bump every ingest + novelty resurfacing)
- Inflated RVOL from compounding live-sim volume
- Cross-ticker RAG attaching wrong filings
- Reset / Mark seen failing silently when a Chrome extension wraps `fetch`

### Changed
- Full engine rescore throttled (~64s); prices still sync ~8s

---

## Template for future entries

```markdown
## [YYYY-MM-DD] - Phase N short title

### Added
- ...

### Changed
- ...

### Fixed
- ...

### Security
- ...
```

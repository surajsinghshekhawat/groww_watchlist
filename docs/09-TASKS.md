# Manual Task Checklist

Simple checklist — no Task Master. Update status here as we go.

Statuses: `todo` · `doing` · `done` · `skipped`

| # | Phase | Task | Status |
|---|-------|------|--------|
| 0 | Docs | Product docs, plan, changelog, development log | done |
| 1–17 | Core product | Scaffold → demo UX+RAG (see history) | done |
| 15 | Stretch | Tier 3 ML | skipped |
| 18 | Web Push | VAPID + service worker + push on alert (tab closed) | done |
| 19 | NLP Watchlist | Intent → LLM extract → catalog match → create list | done |
| 20 | Info tab | Professional explainer (scoring, RAG, LLM, NLP, push) | done |
| 21 | Polish | Wire UI, env docs, verify flows | done |

## Phase 18 — Web Push (when browser tab is closed)

1. Migration `push_subscriptions`
2. Config: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`
3. Send via `pywebpush` when in-app notification is created
4. API: vapid public key, subscribe, unsubscribe
5. Frontend service worker + Settings toggle
6. Docs: `docs/PUSH.md`

## Phase 19 — NLP → watchlist

1. `POST /watchlists/from-intent`
2. LLM structured extract (symbols / sectors / name) — never invents tickers
3. Deterministic match against instrument catalog
4. Create watchlist + add matched names
5. Watchlist tab “Describe a watchlist” UI

## Phase 20 — Info tab

Product thesis, ATTENTION formula, detectors, novelty, confidence, RAG, LLM boundaries, NLP, push, demo limits.

## Phase 21 — Attention feedback loop

1. [x] `event_feedback` table (`useful` / `noise` / `already_knew`)
2. [x] `POST /api/v1/events/{id}/feedback`
3. [x] Digest field `user_feedback`
4. [x] Attention card buttons; noise / already_knew also mark-seen

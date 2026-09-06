# 04 — Methodology

How we build, document, and decide. Follow this for every phase.

---

## Principles (priority order)

When tradeoffs conflict, prefer in this order:

1. Correctness  
2. Security  
3. Core user problem (attention engine, not dashboard)  
4. Data integrity  
5. Explainability  
6. Reliability  
7. UX  
8. Performance  
9. Optional AI  
10. Extra features  

---

## Workflow per phase

```
1. Read phase plan in docs/plans/
2. Log "Starting Phase N" in 07-DEVELOPMENT-LOG.md
3. Implement incrementally (keep app runnable after major steps)
4. Run relevant tests
5. Update FEATURES checkboxes / CHANGELOG / 09-TASKS.md
6. Append "Completed" entry to DEVELOPMENT-LOG with files touched
```

---

## Documentation discipline

### Before a change

- Know which phase / task this belongs to  
- Note intent in `07-DEVELOPMENT-LOG.md`  

### After a change

Append a log entry with:

- **Date / time**
- **Phase / task id**
- **What we did** (1–5 bullets)
- **Files created/modified**
- **Decisions** (if any)
- **Tests run** (and result)
- **Next**

Update `08-CHANGELOG.md` for anything user-visible or architectural.

### Never

- Delete past log entries  
- Skip logging “small” changes during build — append a short line  
- Commit secrets; use `.env.example` only  

---

## Implementation order (locked)

Matches spec §117:

| Phase | Focus |
|-------|--------|
| 0 | Docs & plans (this phase) |
| 1 | Repo skeleton: Next.js, FastAPI, Postgres, Redis, Docker |
| 2 | DB models, migrations, repositories, seed |
| 3 | Auth + authorization |
| 4 | Watchlist CRUD + ownership tests |
| 5 | Market data providers + replay |
| 6 | Analytics: price anomaly, RVOL, market/sector context |
| 7 | MarketEvent pipeline (detect, dedupe, escalate) |
| 8 | Scoring: fusion, significance, confidence, novelty, attention |
| 9 | Digest + mark-seen |
| 10 | WebSocket live updates |
| 11 | Frontend polish (digest UI, evidence, badges) |
| 12 | Tier 2: CUSUM / filings / LLM (flags) |
| 13 | Security hardening |
| 14 | Full test suite + demo script validation |

Do not jump to Tier 2/3 until Tier 1 gates pass.

---

## Ambiguity rule

If the spec is ambiguous:

1. Choose the **simplest** implementation consistent with the product definition  
2. Document the decision in the development log  
3. Do **not** invent a different architecture  

---

## Testing gate

After meaningful backend analytics or auth changes:

- Unit tests for the module touched  
- Security tests when touching authz  
- Do not “fix” tests by deleting coverage  

Before calling the product done (§134):

- Backend tests, frontend tests, security tests  
- Migration + Docker startup  
- Replay demo + WebSocket check  

---

## Task tracking

Use `docs/09-TASKS.md` only (manual). No Task Master / external task MCP.

---

## Git policy

- Commits **only when the user asks**  
- No force-push to main, no config edits, no secret commits  
- Prefer small, reviewable commits when asked  

---

## Communication

- Prefer the attention-engine framing in UI/docs  
- Never use BUY/SELL/guaranteed/will rise language  
- Prefer “unusual movement”, “worth watching”, “filing detected during the move”  

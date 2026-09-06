# Edge cases & refinement backlog

**Purpose:** Deep inventory of failure modes, demo risks, and product ambiguities **before** we change code.  
**Mode:** Living inventory — status table tracks fixes.  
**Date:** 2026-09-05 (updated after continuous-S / trust polish)  

---

## Fix status (2026-09-05)

| ID | Status |
|----|--------|
| C8 | **Fixed** — calibration only for `replay` / `mock` / `live` |
| D2 | **Fixed** — `engine_sync_loop()` interval from mode |
| G1 | **Fixed** — notify only on create/escalate + prior-severity guard |
| B2 | **Fixed** — `empty_hint` + ignored counts on caught-up UI |
| B4 | **Fixed** — market_aligned detail for RVOL-without-residual |
| B5 | **Fixed** — HIGH preferred in top-K + `hidden_high` banner |
| C1 | **Fixed** — `insufficient_history` ignore reason |
| A3 | **Fixed** — reset_seen clears feedback labels |
| A4 | **Fixed** — touch-checked throttled to 15 minutes |
| H3 | **Fixed** — stale digest ignored on playlist switch |
| F2 | **Documented** — novelty is user+instrument (Info tab); per-list later |
| C9 | **Fixed** — continuous Significance inside severity bands |
| C10 | **Fixed** — realistic MAD baseline + z cap (no absurd z≈14 twins) |
| E8 | **Fixed** — template “SYMBOL, is up” stray comma |
| B8 | **Fixed** — digest `headline` one-liner |
| B9 | **Fixed** — `confidence_breakdown` on cards; ignored strip leads Attention UI |
| I5 | **Fixed** — `DEMO_CONFLICT_SYMBOL` / `DEMO_SKIP_CALIBRATION` talk-track knobs |

---

## How to read this

| Severity | Meaning |
|----------|---------|
| **P0** | Can break the judge demo or corrupt trust in the room |
| **P1** | Real product bugs / confusing UX; fix soon after demo polish |
| **P2** | Correctness debt / scale / rare paths |
| **P3** | Nice-to-have hardening |

| Domain | Areas |
|--------|--------|
| A | Novelty / mark-seen / escalation |
| B | Digest / ignore / sensitivity |
| C | Scoring / fusion / detectors |
| D | Market data / prices / modes |
| E | LLM / RAG / NLP |
| F | Auth / multi-list / concurrency |
| G | Alerts / push / feedback |
| H | Frontend / race / extensions |
| I | Demo calibration honesty |

---

## A — Novelty, mark-seen, escalation

### A1 · Same day, two different stories on one name — **P1**
**Edge:** Instrument has a morning volume spike (NOTABLE), user marks seen; afternoon filing arrives (should be HIGH).  
**Expected:** New severity → novelty resurfaces (~0.9).  
**Risk today:** Dedupe reuses one open event and escalates (good) *if* fusion raises severity. If filing merge fails or live refresh strips `filing_present`, severity may not rise → card stays dead.  
**Mitigation idea:** Keep filing-preserve logic (already partially in escalation); add test: seen NOTABLE → inject filing → HIGH resurfaces.

### A2 · Mark-seen on wrong twin event_id — **P1** (mostly mitigated)
**Edge:** Two open events for same symbol (demo + live-sim era).  
**Expected:** Marking one clears all siblings.  
**Status:** Digest picks one “best” event; mark-seen clears all open/escalated siblings.  
**Residual risk:** Feedback keyed by `event_id` may attach to a non-displayed sibling if IDs diverge after rescore.

### A3 · Reset novelty vs feedback labels — **P2**
**Edge:** User labels Noise → cleared; then Reset demo novelty.  
**Expected (demo):** Card returns. Feedback row still says `noise`.  
**Risk:** UI shows old feedback chip on a “fresh” card — confusing.  
**Refine:** Reset clears feedback for that watchlist, or UI ignores feedback when novelty reset for demo.

### A4 · Touch-checked every Attention open — **P2**
**Edge:** Opening Attention stamps `last_checked_at = now` even if user only glances.  
**Product tension:** “Since last check” shrinks immediately; copy may say they were away when they weren’t.  
**Refine:** Touch on leave / explicit “I’m caught up” / only update when mark-seen or after N seconds.

### A5 · Version bump without severity (historical bug) — **P0 mitigated**
**Was:** Live ingest bumped version → novelty resurrected.  
**Now:** Version++ only on severity rise.  
**Keep regression test forever.**

### A6 · Severity *drop* after seen HIGH — **P2**
**Edge:** Event was HIGH, user saw it; later fusion would be NOTABLE.  
**Today:** Same event may stay HIGH until resolved; or stay seen at HIGH with N=0.  
**Rare in demo;** for production need resolve/close criteria when evidence cools.

---

## B — Digest, ignore list, sensitivity

### B1 · Empty watchlist — **P1**
**Edge:** New user, zero instruments.  
**Today:** Empty digest + ignored empty. Register may auto-create starter list — verify all paths.  
**Refine:** Empty state CTA: “Add names or describe a watchlist.”

### B2 · All ignored / “You’re caught up” while market is hot — **P1**
**Edge:** Sensitivity HIGH + everything market_aligned or already_seen.  
**Risk:** Looks broken (“app shows nothing”).  
**Refine:** Caught-up copy should cite *why* (sensitivity / seen / aligned) with counts.

### B3 · market_aligned vs HIGH filing — **P0** for story
**Edge:** Reliance-like residuals but filing suddenly true.  
**Expected:** Not suppressed (filing short-circuits ignore).  
**Verify:** Ignore gate requires `not filing`. Keep test.

### B4 · RVOL high but residuals tiny, no filing — **P2**
**Edge:** Pure liquidity spike, market-aligned.  
**Today:** May be NOTABLE via `has_market` only, then possibly shown if not caught by market_aligned (aligned gate also needs weak price z).  
**If RVOL alone sets has_market and z is high:** card shows.  
**If z low and RVOL high:** has_market true → NOTABLE; market_aligned requires z < notable_price_z — RVOL-only notable can still appear.  
**Product question:** Should volume-only market-aligned moves be ignored? (Probably yes for “attention” purity.)

### B5 · Top-K hides a High — **P1**
**Edge:** Six HIGHs, `TOP_K=5`.  
**Risk:** Sixth High invisible with no “+1 more”.  
**Refine:** Summary “3 more High not shown” or raise K for HIGH floor.

### B6 · Ignored reason collisions — **P3**
**Edge:** Same name could be already_seen and below_sensitivity; first wins.  
**OK for demo;** document precedence: severity LOW → sensitivity → novelty → attention → market_aligned → no_event.

### B7 · Sensitivity change mid-session — **P2**
**Edge:** User flips to HIGH sensitivity; cards vanish without animation/explanation.  
**Refine:** Toast: “Filtered by sensitivity.”

### B8 · Digest lacks elevator pitch — **P2** → **Fixed**
**Now:** `summary.headline` one-liner under the Attention title.

### B9 · Confidence unexplained on card — **P2** → **Fixed**
**Now:** `confidence_breakdown` + ignored strip rendered **above** Attention cards.

---

## C — Scoring, fusion, detectors

### C1 · Insufficient history — **P1**
**Edge:** New instrument, &lt;2 price points.  
**Today:** Skipped in `score_watchlist_instruments`. No event → ignored `no_event`.  
**Looks like “quiet”** even if Yahoo just failed.  
**Refine:** Distinguish `insufficient_history` vs truly quiet.

### C2 · Zero / negative prices — **P2**
**Edge:** Bad provider tick.  
**Risk:** Returns explode or MAD breaks.  
**Refine:** Reject non-positive prices at ingest.

### C3 · Index as watchlist item — **P2**
**Edge:** User adds NIFTY50 to list.  
**Today:** Scoring skips `is_index`. Digest may show no_event forever.  
**Refine:** Disallow add, or show “index used for context only.”

### C4 · Sector without peers — **P3**
**Edge:** Alone in sector → empty peers. Fine.

### C5 · Information → always HIGH — **P1 product**
**Edge:** Tiny housekeeping filing in corpus.  
**Today:** `has_information` ⇒ HIGH.  
**Risk:** Over-alert if live filings are noisy.  
**Refine:** Filing materiality grades (demo OK; production needs taxonomy).

### C6 · Coarse β wrong sign / magnitude — **P2**
**Edge:** Seeded betas bad → residual false positives/negatives.  
**Demo:** Calibration forces Reliance.  
**Production:** Rolling OLS (Tier 3).

### C7 · MAD with flat history — **P2**
**Edge:** MAD≈0 → insufficient_data → z=0. Correct (no invented signal).

### C8 · Demo calibration overrides live truth — **P0 honesty / P2 product**
**Edge:** Yahoo mode still runs `_CALIBRATION` overlays for HDFC/Reliance/TCS.  
**Risk:** “Live” prices with scripted severity — worst of both worlds.  
**Status:** **Fixed** — calibration only for `replay` / `mock` / `live`; never yahoo. `DEMO_SKIP_CALIBRATION` turns overlays off entirely for an unscripted beat.

### C9 · Flat Significance within band — **P0 credibility** → **Fixed**
**Was:** WORTH_WATCHING always \(S=0.7\) → identical Attention for same N·C (TCS/INFY twin 0.56).  
**Now:** Continuous \(S\) inside band from evidence excess (`significance_continuous`).

### C10 · Absurd z from near-flat synthetic window — **P0 credibility** → **Fixed**
**Was:** ±0.2% quiet series → MAD collapse → z≈14 for every mid move.  
**Now:** Realistic ~1% baseline window + `MAX_PRICE_ANOMALY_Z` cap.

---

## D — Market data & modes

### D1 · Replay vs live-sim clock skew — **P1 mitigated**
**Edge:** Replay timestamps on Sep 4; live-sim “now”. Filings window, dedupe, age.  
**Mitigations exist** (filing day fallback, dedupe reuse).  
**Still:** `data_age_seconds` / “last checked” copy can confuse. Label mode clearly.

### D2 · main.py forces `engine_sync_loop(8.0)` — **P1**
**Edge:** Yahoo mode wanted ~45s interval; lifespan passes `8.0` always.  
**Effect:** Hammer Yahoo → 429s → empty/cache tape.  
**Refine:** Pass `None` so loop picks interval from mode.

### D3 · Yahoo rate limit / empty snapshot — **P1**
**Edge:** All symbols 429; cache cold; DB fallback old replay prices mixed with source labels.  
**Risk:** Attention on stale hybrid tape.  
**Refine:** Degrade banner “Yahoo unavailable — last good quotes”; don’t rescore if ingest=0.

### D4 · Market closed / weekend — **P2**
**Edge:** Yahoo last close unchanged; live-sim still wiggles.  
**Refine:** Session clock badge (open/closed).

### D5 · Switching mode mid-run without restart — **P1**
**Edge:** Change `.env` but uvicorn reload may not reload settings; or settings reload but tape WS still live-sim.  
**Refine:** Document restart; health endpoint shows effective mode + last ingest source.

### D6 · PricePoint table unbounded growth — **P2**
**Edge:** 8s ingest forever.  
**Risk:** Disk/CPU; hist loops load all points ascending.  
**Refine:** Retention window / downsample.

### D7 · Corporate action adjust wrong day — **P3**
Demo CA catalog only.

---

## E — LLM, RAG, NLP

### E1 · LLM timeout → ugly fallback on HIGH — **P1**
**Edge:** Groq slow; `_local_paraphrase` or template.  
**Risk:** Inconsistent tone. Prefer clean template always on failure.

### E2 · LLM invents causality despite prompt — **P1**
**Edge:** Model adds “due to RBI” not in evidence.  
**Refine:** Post-check / shorter prompt / temperature 0; show “Narrated from evidence” badge.

### E3 · RAG wrong doc despite symbol filter — **P2**
**Edge:** CONTEXT-BANKING.md mentions many banks.  
**Mitigation:** symbol in source/title. Keep strict prefix match preferred.

### E4 · NLP count “top 4” vs LLM returns 8 — **P2 mitigated**
Cap enforced in plan/resolve. Re-test after model changes.

### E5 · NLP + empty catalog match — **P1**
**Edge:** User says “EV stocks” — no catalog hits.  
**Today:** 422 NO_MATCHES. Good. Copy must stay helpful.

### E6 · Concurrent NLP confirm double-create — **P3**
Double-click → two playlists. Debounce UI.

### E7 · Notes pollution — **P1 mitigated**
Ugly “Matched keywords… LLM unavailable” notes cleaned; notes never boost scores.

### E8 · Template stray comma — **P0 polish** → **Fixed**
**Was:** `", ".join([symbol, "is up…"])` → “TCS, is up 3.2%…”.  
**Now:** Space-joined clauses in `templates.py`.

---

## F — Auth, multi-list, concurrency

### F1 · Watchlist version 409 — **P2**
Two tabs edit same list. Need clear UI on 409.

### F2 · Digest for list A, mark-seen affects instrument globally — **P1**
**Edge:** Snapshots are per `(user, instrument)`, not per watchlist.  
**Mark seen on List A hides same name on List B.**  
**Product decision:** Global memory (current) vs per-list memory. Document; maybe per-list later.

### F3 · Delete watchlist while WS subscribed — **P2**
WS should 4404 / stop; client should fall back.

### F4 · Register without email verify — **P3** demo OK.

### F5 · Token expiry mid-demo — **P1**
JWT 60m; long judge day → sudden logout. Refresh or longer demo TTL.

---

## G — Alerts, push, feedback

### G1 · Alert spam on every rescore — **P1**
**Edge:** Worker notifies each score cycle for same HIGH.  
**Need:** Notify only on create / severity escalate / novelty-positive. Audit `notify_owners_for_event`.

### G2 · Push when no permission / keys missing — **P2**
UI should not claim “enabled” if `configured: false`.

### G3 · Feedback without watchlist_id — **P2**
Noise may not mark-seen if id omitted. UI always sends id — API should require it for noise/knew.

### G4 · useful then noise — **P3**
Upsert overwrites; second clears. OK.

---

## H — Frontend races & environment

### H1 · Chrome extension breaks fetch — **P0 demo ops**
Documented Incognito. Keep banner in DEMO.

### H2 · Optimistic mark-seen then digest refresh restores card — **P1**
**Edge:** Race with engine rescore / novelty bug.  
**If returns:** P0 for trust. Watch in rehearsal.

### H3 · Stale React state after playlist switch — **P1**
Switch list while digest in flight → wrong list’s cards. Cancel/ignore stale responses.

### H4 · Attention touch + WS refresh fight — **P3**

### H5 · SSR/hydration — **P3** if any.

---

## I — Demo calibration & competition honesty

### I1 · Judges ask “is this real-time?” — **P0 narrative**
Answer: replay + live-sim; architecture supports providers; Yahoo optional not pitch.

### I2 · Eval 5/5 but UI wrong — **P0**
Always re-run `demo_pipeline` before room. Checklist in DEMO.md.

### I3 · Calibration in non-demo modes — **P1** (see C8)

### I4 · Info tab vs live UI drift — **P2**
Keep Info panel in sync with scoring story (continuous S, conflict demo).

### I5 · Confidence gate never visible in replay — **P1** → **Fixed (demo knob)**
**Was:** Replay forces freshness=1.0; judges never saw DATA_CONFLICT.  
**Now:** `DEMO_CONFLICT_SYMBOL` (default **TCS**) injects dual-source disagreement on digest.  
`DEMO_SKIP_CALIBRATION` for unscripted 10s beat.  
**Caveat:** Demo sensitivity must be **MEDIUM** (seed resets HIGH → MEDIUM); HIGH sensitivity hides Worth-watching cards including the conflict beat.

---

## Cross-cutting “deep” scenarios (stories)

### Story 1 — Gap and catch-up
User away 3 days; many escalations; opens app.  
**Want:** Ordered High digest, not 40 cards. Top-K + sensitivity.  
**Gap:** No “session briefing” summary count of suppressed.

### Story 2 — Whipsaw
Stock spikes (HIGH), user marks seen, reverts, spikes again same severity.  
**Want:** Same severity → stays seen (no spam) **or** time-based re-open policy.  
**Today:** Same severity stays N=0 — correct for anti-spam; may miss “second episode.”  
**Product fork:** New event if resolved+cooled, else stay quiet.

### Story 3 — Sector crash
All banks −4% with index −3.8%.  
**Want:** Mostly market_aligned suppress; maybe one weird name.  
**Risk:** Coarse β wrong → all fire or none fire.

### Story 4 — Filing without price move
Board outcome, flat price.  
**Today:** Information → HIGH. Good for “attention ≠ movement.”  
**Edge:** Spammy filings → need materiality.

### Story 5 — Partial provider failure
Half Yahoo symbols fail.  
**Want:** Show partial tape + confidence demotion on missing.  
**Today:** Cache/DB mix; confidence may still be high in replay mode.

### Story 6 — Dual list, one name
See F2.

---

## Suggested fix order (when you say go)

### Wave 1 — Demo safety (before judges)
1. **C8 / I3** — Calibration only in replay/live-sim, never yahoo  
2. **D2** — Don’t force 8s interval when yahoo (or ignore if staying replay-only)  
3. **G1** — Notify only on escalate/create  
4. **H3** — Ignore stale digest responses on list switch  
5. **B2** — Richer caught-up empty state  
6. Rehearse **H2** mark-seen race on real machine  

### Wave 2 — Product correctness
7. **F2** — Document or fix per-list novelty  
8. **B4** — Volume-only aligned ignore policy  
9. **B5** — Overflow High indicator  
10. **C1** — insufficient_history reason  
11. **A3** — Feedback vs reset interaction  
12. **A4** — Touch-checked policy  

### Wave 3 — Hardening
13. **D6** price retention  
14. **C5** filing materiality  
15. **E2** narration guardrails  
16. **D3** yahoo degrade UX  

---

## What we are *not* treating as bugs

- Replay not being live exchange data  
- Demo calibration for HDFC/Reliance (required for CODE story) *in replay*  
- LLM optional / offline heuristic NLP  
- No buy/sell  
- Top-K truncating by design (but overflow UX is a refine)  

---

## Next step

You pick:

1. **Wave 1 only** (demo armor), or  
2. **Wave 1 + specific IDs** (e.g. F2, B5, G1), or  
3. **Full triage implementation** top-down  

Then we implement and add regression tests where it matters (novelty, calibration guard, notify-once).

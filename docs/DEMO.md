# Live demo script (judges)

**Product:** State-aware attention for a watchlist — not a price predictor.  
**Say out loud:** `ATTENTION = SIGNIFICANCE × NOVELTY × CONFIDENCE`  
**Punchline:** *We don’t show everything that moved — we show the smallest novel trustworthy set, and we show what we refused to show.*

**Must:** `MARKET_DATA_MODE=replay` · use **Incognito** if Mark seen / Reset fail (browser extensions).

---

## 0) Prep (5 min before)

```powershell
cd "path\to\groww - watchlist"
docker compose up -d postgres redis

cd backend
alembic upgrade head
python -m app.seed
python -m app.demo_pipeline
python -m app.eval
```

Expect eval **5/5**. If Attention is noisy, re-run `demo_pipeline` and hard-refresh.

```powershell
# Terminal A
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal B
cd frontend
npm run dev
```

- UI: http://localhost:3000  
- Login: `demo@example.com` / `DemoPass123!`  
- Optional LLM: [LLM.md](./LLM.md) (`ENABLE_LLM=true` + Groq)

**Env knobs for talk-track beats**

| Var | Default | Use |
|-----|---------|-----|
| `DEMO_CONFLICT_SYMBOL` | `TCS` | Forces `DATA_CONFLICT` + lower C on that card — show resilience live (needs **MEDIUM** sensitivity so the card is visible) |
| `DEMO_SKIP_CALIBRATION` | `false` | Set `true` for ~10s, re-run `demo_pipeline`, show raw math (uncalibrated moment) |

---

## 1) Opening (15–20 sec)

**Say:**  
“This is a **smart market watchlist**. Groww already shows prices. We decide **what deserves attention** after your last check — significance, novelty, and confidence. The LLM never decides importance.”

**Show:** tabs Market · Watchlist · Attention · Alerts · Settings · Info.

---

## 2) Watchlist (45–60 sec)

| Beat | Do | Say |
|------|-----|-----|
| A | Point at list (HDFC, Reliance, TCS, …) | “Identity is by **instrument**, not ticker string.” |
| B | Add a name | “You curate like Groww — we only score what you care about.” |
| C | Optional note | “Notes explain; they never boost the score.” |
| D | Optional NLP chip (“IT peers of TCS…”) / “exactly 4 stocks” | “Planner suggests; **catalog match only** — count is enforced.” |

**Transition:** “Given this list — what should interrupt you?”

---

## 3) Attention (90–120 sec) — *hero*

### Lead with ignored (aha first)

| Beat | Point | Say |
|------|-------|-----|
| Headline | One-liner under the title | “Elevator pitch of the digest — High / Watch / noise.” |
| **Ignored strip** | *What we ignored* (above cards) | “Attention is scarce. Reliance moved with the market — **suppressed**. Movement ≠ attention.” |

### Ranking

| Beat | Point | Say |
|------|-------|-----|
| Formula | `S · N · C` | “Miss any one and attention collapses. **S is continuous inside each severity band** — same tier, different numbers.” |
| **HDFC HIGH** | Top card | “Filing + anomaly + RVOL + CUSUM → **High**.” |
| Evidence | Expand | Walk z, RVOL, residuals, CUSUM, filing — z should look sane, not absurd. |
| Confidence line | Under C | “Single source / conflict / freshness — we show why C isn’t 1.0.” |
| Conflict beat | TCS card | “Sources disagree → `DATA_CONFLICT`, confidence collapses.” |
| Peers | Peer row | “Idiosyncratic vs sector beta.” |
| Retrieval | RAG chips | “Local filing corpus — provenance. LLM narrates; doesn’t invent numbers.” |
| TCS vs peers | Milder / different S | “Same band label can still differentiate — continuous significance.” |

### Novelty + feedback

| Beat | Do | Say |
|------|-----|-----|
| Mark seen | On HDFC | “Acknowledged → novelty 0 → leaves digest.” |
| Feedback | Useful / Noise / Already knew | “Honest labels — no public ‘meaningful’ dataset. Noise also clears.” |
| Reset | Reset demo novelty | “Clears seen-state for demos; escalation would resurface.” |

### Optional: uncalibrated 10s

1. Stop API. Set `DEMO_SKIP_CALIBRATION=true`. Re-run `python -m app.demo_pipeline`. Restart API.  
2. Show Attention briefly: “Same detectors, no story overlays.”  
3. Flip back to `false`, re-run pipeline, continue scripted story.

### Prices under digest

**Say:** “Same persisted prices the engine used — Attention is grounded in this tape.”

---

## 4) Market (20–30 sec, optional)

**Say:** “Live-sim board — same feed syncs into the engine. **No exchange API required for the demo.**”

---

## 5) Alerts + Settings (30–40 sec)

| Beat | Say |
|------|-----|
| Alerts | “Attention-gated — not every tick. Create/escalate once — no spam duplicates.” |
| Sensitivity | “Stricter → smaller digest.” |
| Web Push | “Optional OS push when the tab is closed (VAPID).” |

---

## 6) Close (10 sec)

**Say:**  
“Watchlist is the input. Scoring is the product: **S × N × C**, with evidence, retrieval, and an explicit ignore list. Ready to sit on Groww’s surface later — today it’s a focused demo of attention with memory.”

---

## Timing

| Length | Path |
|--------|------|
| **~2 min** | Attention: ignored → headline → HDFC → mark-seen → punchline |
| **~4 min** | + Watchlist + Market + Alerts |
| **~6 min** | + NLP “exactly 4” + conflict beat + `app.eval` 5/5 |

---

## FAQ one-liners

| Question | Answer |
|----------|--------|
| Predict price? | No — rank **attention** after last check. |
| LLM score? | No — fusion scores; LLM narrates only. |
| Why discrete bands? | Labels for UI; **S is continuous inside the band** from how far past thresholds evidence sits. |
| Why no ML? | No public ground-truth of “deserved attention” — feedback labels are the honest path. |
| Why ignore Reliance? | Market residual below threshold. |
| Sources disagree? | `DATA_CONFLICT` → agreement collapses → C (and Attention) drop. Demo: TCS (`DEMO_CONFLICT_SYMBOL`). |
| Live markets? | Judge path = **replay + live-sim**. Optional `yahoo` exists; not the pitch. |
| Canned? | Flip `DEMO_SKIP_CALIBRATION` for a raw beat. |
| Push? | Web Push in Settings; in-app alerts always. |

---

## Checklist

- [ ] `MARKET_DATA_MODE=replay`  
- [ ] `/health` ok  
- [ ] `python -m app.eval` → all PASS  
- [ ] Attention: **headline** + **ignored first** + **HDFC HIGH**  
- [ ] Cards: no “TCS, is up…” comma; **confidence breakdown** visible  
- [ ] TCS (or `DEMO_CONFLICT_SYMBOL`) shows conflict / lower C  
- [ ] TCS / peers Attention scores **not** identical twins when both shown  
- [ ] Sensitivity = **MEDIUM** (seed resets this; HIGH hides Worth-watching cards)  
- [ ] Mark seen removes card; Reset restores  
- [ ] Feedback buttons visible  
- [ ] Record a fallback video of this flow  
- [ ] Incognito if fetch fails  

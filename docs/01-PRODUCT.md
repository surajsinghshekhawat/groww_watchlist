# 01 — Product Vision

**What we are building:** a state-aware attention-ranking engine for equity watchlists (Groww CODE 2026).

---

## One-sentence definition

> Detect unusual movement relative to a stock’s own history and its market/sector context, corroborate with real events, remember exactly what event state the user has already seen, and surface only the smallest set of changes that deserve attention — each with an evidence-grounded explanation.

---

## Problem

Existing watchlists and price alerts answer “what is the price now?” or “did X% cross?” They do **not** answer:

> Out of everything that happened while I was away, what is the smallest, highest-value set of things I need to see — and can you prove, in one sentence, why each made the cut?

---

## Product bet

This is **attention ranking with memory**, not forecasting.

Users return after minutes or hours. The system must:

1. Know what changed on their instruments
2. Judge whether changes were *unusual* for that stock
3. Compare to market and sector context
4. Check persistence and corroborating information
5. Assess data trustworthiness
6. Know whether *this user* already saw *this event state*
7. Rank a small top-K set
8. Explain each item from verified evidence only

---

## Core scoring model (non-negotiable)

```
SIGNIFICANCE  — objective unusualness / importance right now
NOVELTY       — new to this user at this event state?
CONFIDENCE    — trust in underlying data?

ATTENTION = SIGNIFICANCE × NOVELTY × CONFIDENCE
```

### Load-bearing rules

| Rule | Why |
|------|-----|
| Time-away must **not** inflate significance | Absence is user behavior, not a market fact |
| Novelty is event-state-aware | Escalation (NOTABLE → HIGH) must resurface |
| LLM never judges significance | Unreliable and unexplainable |
| Never key on ticker string | Renames / category changes orphan watchlists |
| Stale/conflicted data lowers confidence | Prevents confident false alerts |
| Severity labels are discrete; \(S\) is continuous inside the band | Same tier can still differentiate Attention |

---

## What “meaningful” means here

There is **no public ground-truth dataset** of “meaningful vs not” at scale. That is a documented data gap, not an oversight.

Therefore we use an **interpretable, evidence-based** system (rules + statistics), not a black-box classifier trained on non-existent labels. ML may later act as a candidate generator / reranker only.

---

## Explicit non-goals

We will **not** build:

- Price prediction (LSTM / Transformer / “will rise”)
- Trading bot / buy-sell recommendations
- Full RSI/MACD technical-indicator suite
- Ungrounded LLM “analyst”
- RL personalization
- Kubernetes / Kafka / microservice sprawl

---

## Primary user loop

```
OBSERVATION → FEATURE → ANOMALY → EVENT → EVIDENCE
  → SIGNIFICANCE → USER STATE → NOVELTY → CONFIDENCE
  → ATTENTION → RANK → EXPLAIN
```

UI hierarchy:

1. **What changed?**
2. **Why does it matter?**
3. **How confident are we?**

---

## Demo narrative (must work)

1. Watchlist: HDFC Bank, Reliance, TCS, Infosys, ICICI Bank  
2. Last checked ~10:00  
3. Replay 10:00 → 14:00  
4. HDFC: +4.2% vs Nifty +0.6% / sector +1.1%, RVOL 4.1×, filing → **HIGH**  
5. Reliance: moves with market → lower attention  
6. Mark-seen hides HDFC; later escalation resurfaces it  

---

## Honest framing for judges

- Interpretable scoring over fake ML because labels don’t exist at scale  
- User feedback (**useful / noise / already knew**) is how we collect honest labels  
- Coarse beta v1 over live OLS for calibration risk  
- CUSUM is corroboration only  
- Template explanation fallback if LLM is unavailable  
- Judge path = **replay + live-sim** — change-detection, not prediction — by design  
- Optional Yahoo / broker feeds are architecture-ready, not required for the demo story  

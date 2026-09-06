# Suggestion analysis — scoring credibility & priority list

**Purpose:** Honest compare of the external critique against what this codebase *actually* does.  
**Verdict first, then item-by-item.**  
**Date:** 2026-09-05  
**Status:** Must-list (#1/#3/#5/#6/#13/#14 + demo craft docs) **implemented** 2026-09-05. Remaining: manual retests (#2/#4), optional Maybe items.

---

## 1. Core claim: Is scoring proper, original, “smart”?

### Proper — **Agree: yes**

MAD robust z, TOD RVOL, β residuals, CUSUM-as-corroboration-only, grouped fusion, confidence as a multiplicative gate — these are real techniques used in the right roles. The architecture is not hand-wavy.

### Original (as synthesis) — **Agree: yes, with a careful claim**

Individual pieces are not novel. The **combination** is a fair originality claim for CODE:

- \(A = S \times N \times C\)
- **Event-state** novelty (not “time since last open”)
- Explicit **ignored + why**
- LLM narrates, never scores

Do **not** claim “we invented RVOL” or “we invented beta.” Claim the **product synthesis**.

### Smart (as currently *demonstrable*) — **Agree: this is the weak spot**

The TCS / INFY collision (same Attention **0.56**, same S/N/C) is **not primarily a mystery MAD bug**. It is largely **by construction** in the current code:

| Factor | How it’s computed today | Effect |
|--------|-------------------------|--------|
| **S** | Flat map from severity band: LOW 0.1 / NOTABLE 0.4 / WORTH_WATCHING **0.7** / HIGH 1.0 | Any two WORTH_WATCHING names → **identical S** |
| **N** | 1.0 if never marked seen | Identical for both |
| **C** | Often **0.8** (single-source agreement) in replay | Identical for both |
| **A** | \(0.7 \times 1.0 \times 0.8 = \mathbf{0.56}\)** | **Must collide** |

So even if z-scores were 4 vs 40, **Attention would still match** once both fuse to the same severity band. The critique slightly misplaces the root cause on “MAD saturation alone”; the **higher-leverage bug/design gap is step-function Significance (#6)**, with MAD/window quality (#1) as a separate credibility issue for the *evidence chips* (z ≈ 14.x for everything looks absurd to a stats-literate judge).

Also: demo **calibration** forces TCS z to `notable_price_z + 0.2` — so TCS’s z is partly scripted, not pure MAD. That amplifies “why do different % moves look the same?”

**Bottom line on the thesis:** Architecture and framing are smart. **Numbers on the card are currently coarse.** Fixing continuous S (and cleaning z display) is what makes the pitch honest.

---

## 2. Item-by-item: worth it? makes sense? vs our reality

Legend: **Do** / **Maybe** / **Skip (for CODE)** · **Sense** = technically/product-correct · **Leverage** = impact on judges

### A — Must-fix bugs

| # | Suggestion | Sense? | Worth for CODE? | Comment |
|---|------------|--------|-----------------|--------|
| **1** MAD/z saturation | **Yes** (partial) | **Do** | z≈14 for every mid move looks fake. Fix window / fixture / don’t show absurd z; but **Attention equality is mostly #6**, not only MAD. Sanity: 1% vs 4% should differ in **evidence z**, even if tier label is shared. |
| **2** Dedupe SBIN alerts | **Yes** | **Do** (verify) | We already notify-once on create/escalate. **Re-test Alerts tab** before demo — cheap. Don’t rebuild if clean. |
| **3** “TCS, is up” comma | **Yes** | **Do** | Cheap, visible every card. Templates/LLM. Fix immediately. |
| **4** NLP “exactly 4” | **Yes** | **Do** (retest) | Count cap was added; **explicit retest** still required. 5 min. |
| **5** Stage a confidence failure | **Yes** | **Do** (small) | Replay forces C freshness=1.0 by design — correct for demo stability, but kills the resilience story. A **one-instrument scripted stale/conflict** for the talk track is high demo value, low code risk. |

### B — Make scoring smarter

| # | Suggestion | Sense? | Worth for CODE? | Comment |
|---|------------|--------|-----------------|--------|
| **6** Continuous S within band | **Yes — best diagnosis** | **Do first** | Highest strategic fix. Keep UI tiers; let \(S\) vary (e.g. 0.55–0.85 inside WORTH_WATCHING from fused strength / z percentile). Directly kills TCS/INFY Attention twins. |
| **7** Peer divergence into score | **Yes** | **Maybe** | Data already exists. Light weight into context group is coherent. **Don’t** let it dominate fusion before #6 ships. Medium leverage. |
| **8** Feedback → live adaptive loop | **Yes in principle** | **Maybe / thin stub** | Full tuner is Wave 3. A **session-local** “3× Noise → toast + nudge sensitivity” is demo-candy and matches “smart.” Risky if it surprises judges mid-script — keep optional/settings. |
| **9** Retrospective “did HIGH matter?” | **Yes** | **Maybe (time)** | Persuasive if honest. With **calibrated demo**, backtest can look circular (“we flagged what we scripted”). Only worth it if framed as **eval harness / offline check on replay**, not fake alpha. High leverage *if* credible; otherwise skip. |

### C — Stand-out additions

| # | Suggestion | Sense? | Worth for CODE? | Comment |
|---|------------|--------|-----------------|--------|
| **10** Sector bundling | **Yes** | **Maybe** | Fits “attention is scarce.” Non-trivial UX. Nice differentiator; **after** #6/#3. |
| **11** Non-scripted live moment | **Yes** | **Do (demo craft)** | More presentation than feature: 10s with calibration off / raw live-sim. Preempts “canned.” **Highest demo ROI per minute** after #6. |
| **12** Portfolio / holdings stub | **Yes for Groww** | **Maybe** | Smart Groww-context. Stub “you hold N shares” is fine; don’t block on Groww API (paid). |
| **13** One-sentence digest header | **Yes** | **Do** | Cheap, on-brand, instant pitch. Template from summary counts — no LLM required. |

### D — Trust & polish

| # | Suggestion | Sense? | Worth for CODE? | Comment |
|---|------------|--------|-----------------|--------|
| **14** Explain why C=0.8 | **Yes** | **Do** | We already compute freshness/agreement/completeness — just surface them. Aligns with “show your work.” |
| **15** Model/version tag | **Weak-medium** | **Skip or tiny** | Nice engineering signal; low judge attention. Optional footer. |
| **16** Mobile check | **Yes** | **Do (30–60 min)** | Cheap insurance; don’t redesign. |

### E — Demo prep

| # | Suggestion | Sense? | Worth for CODE? | Comment |
|---|------------|--------|-----------------|--------|
| **17** Fallback video | **Yes** | **Do** | Non-negotiable stage risk hedge. |
| **18** Rehearse answers | **Yes** | **Do** | Especially: discrete bands (→ continuous S story), no ML labels, DATA_CONFLICT live. |
| **19** Lead with ignored strip | **Yes** | **Do** | Already in DEMO.md — **execute** it live; best aha. |

### F — If time allows

| # | Suggestion | Sense? | Worth for CODE? | Comment |
|---|------------|--------|-----------------|--------|
| **20** Rolling OLS | **Yes later** | **Skip now** | Correct Tier 3; won’t save the pitch if #6 undone. |
| **21** FinBERT | **Optional** | **Skip now** | Easy to look gimmicky; LLM/RAG already contested. |
| **22** Isolation Forest | **OK as candidate-only** | **Skip now** | Your own non-goal discipline. |
| **23** Feedback batch job | **Yes later** | **Skip now** | Endpoint of #8; not demo-critical. |

---

## 3. Where the critique is slightly wrong or overstated

1. **“z saturation is why Attention matches”** — Incomplete. **Flat S from severity** guarantees matching Attention for same tier + N + C. Fix #6 even if MAD is perfect.  
2. **“Smart isn’t there”** — Too harsh on architecture; fair on **demonstrable differentiation**. Novelty + ignore strip *are* smart; the **score printout** isn’t fine-grained yet.  
3. **Backtest (#9) as #1 proof** — Dangerous with calibrated HDFC story. Prefer: continuous S + ignored strip + optional uncalibrated live-sim beat.  
4. **Feedback must change thresholds live (#8)** — Nice, not definitional for CODE. Persisting labels already matches your PRD honesty; live nudge is bonus.

---

## 4. Recommended priority (reconciled)

### Must before deadline (high sense + high leverage)

1. **#6 Continuous significance within band** (kills identical 0.56)  
2. **#1 Clean z / history so evidence chips aren’t absurd** (supports #6)  
3. **#3 Template comma**  
4. **#13 Digest one-liner header**  
5. **#14 Confidence breakdown on card**  
6. **#2 / #4 retests** (alerts dedupe, NLP count)  
7. **#11 + #19 + #17 + #18** demo craft (uncalibrated moment, lead ignored, video, answers)  
8. **#5 One staged confidence/conflict beat**  

### Only if time

- #7 peer into fusion (light)  
- #8 thin feedback toast  
- #10 sector bundle  
- #12 holdings stub  
- #16 mobile sniff  

### Explicitly deprioritize for CODE

- #20–23 ML/OLS/FinBERT/IF  
- Heavy #9 backtest unless framed as offline eval, not “live alpha”

---

## 5. One-sentence strategic take

The critique is **directionally right and strategically useful**: your originality is the **system**, but judges will judge the **numbers on the card**. Continuous \(S\) + non-absurd z + ignored-strip-led demo + one unscripted beat matters more than FinBERT, OLS, or a fake portfolio API.

---

## 6. Suggested next build order (when you say implement)

```
1. Fix template comma (#3)                         ✅ done
2. Continuous S within severity (#6) + z sanity (#1) ✅ done
3. Confidence breakdown UI (#14) + digest header (#13) ✅ done
4. Scripted DATA_CONFLICT / stale demo beat (#5)   ✅ done (DEMO_CONFLICT_SYMBOL=INFY)
5. Retest alerts + NLP 4 (#2, #4)                  — manual before stage
6. Demo: calibration-off 10s + lead ignored (#11, #19) ✅ DEMO.md + IgnoredStrip first
```

Implemented 2026-09-05 — see DEMO.md for judge talk-track.

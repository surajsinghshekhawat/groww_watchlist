# Smart Market Watchlist — Documentation Index

**Project:** Groww CODE 2026 · Smart Market Watchlist  
**Status:** Competition demo-ready (Tier 1 + Tier 2) — **[DEMO.md](./DEMO.md)**  
**Default data:** `MARKET_DATA_MODE=replay`  
**Last updated:** 2026-09-07  
**Scoring note:** Continuous \(S\) inside severity bands; see [SUGGESTION-ANALYSIS.md](./SUGGESTION-ANALYSIS.md) (must-list implemented).

This folder is the source of truth for product, architecture, and changes.

---

## Judges — read in this order

| # | Doc | Purpose |
|---|-----|---------|
| 1 | [DEMO.md](./DEMO.md) | Live walkthrough + checklist |
| 2 | [ARCHITECTURE-OVERVIEW.md](./ARCHITECTURE-OVERVIEW.md) | System diagram + Mermaid flows |
| 3 | [DECISIONS.md](./DECISIONS.md) | Considered / deferred / rejected (and why) |
| 4 | [PROJECT-COMPLETE.md](./PROJECT-COMPLETE.md) | Full technical + product deep dive |
| 5 | [01-PRODUCT.md](./01-PRODUCT.md) | Problem, formula, non-goals |
| 6 | [03-FEATURES.md](./03-FEATURES.md) | Shipped feature list |
| 7 | [05-ARCHITECTURE.md](./05-ARCHITECTURE.md) | Locked design notes |
| 8 | [API.md](./API.md) | HTTP + WebSocket |
| 9 | [SECURITY.md](./SECURITY.md) | Threat model |

Repo entry: **[../README.md](../README.md)** — live demo + video links

---

## Full map

| Doc | Purpose |
|-----|---------|
| [ARCHITECTURE-OVERVIEW.md](./ARCHITECTURE-OVERVIEW.md) | **Architecture diagram + Mermaid** (judge-friendly) |
| [PROJECT-COMPLETE.md](./PROJECT-COMPLETE.md) | **Complete project reference** (math, features, integrations, strategy) |
| [DECISIONS.md](./DECISIONS.md) | Approaches considered, deferred, rejected |
| [EDGE-CASES.md](./EDGE-CASES.md) | Edge-case inventory & fix waves (analysis before patches) |
| [SUGGESTION-ANALYSIS.md](./SUGGESTION-ANALYSIS.md) | External critique vs codebase — what to build for CODE |
| [01-PRODUCT.md](./01-PRODUCT.md) | Product definition, scoring model |
| [02-TECH-STACK.md](./02-TECH-STACK.md) | Languages, frameworks, infra |
| [03-FEATURES.md](./03-FEATURES.md) | Tier 1 / 2 / 3 + out-of-scope |
| [04-METHODOLOGY.md](./04-METHODOLOGY.md) | How we build and decide |
| [05-ARCHITECTURE.md](./05-ARCHITECTURE.md) | Data flow and components |
| [06-IMPLEMENTATION-PLAN.md](./06-IMPLEMENTATION-PLAN.md) | Phased build plan |
| [07-DEVELOPMENT-LOG.md](./07-DEVELOPMENT-LOG.md) | Running diary |
| [08-CHANGELOG.md](./08-CHANGELOG.md) | Notable changes |
| [09-TASKS.md](./09-TASKS.md) | Phase checklist |
| [API.md](./API.md) | API reference |
| [DEMO.md](./DEMO.md) | Judge script |
| [SECURITY.md](./SECURITY.md) | Controls |
| [LLM.md](./LLM.md) | Optional Groq/Gemini + RAG |
| [PUSH.md](./PUSH.md) | Web Push (VAPID) |
| [plans/](./plans/) | Phase plans |

---

## Documentation rules

1. Before a phase: plan under `plans/` + intent in `07-DEVELOPMENT-LOG.md`.  
2. After a change: append log + update `08-CHANGELOG.md` / `09-TASKS.md`.  
3. Never delete history from the development log — only append.  
4. Decisions go under a `Decision:` heading in the log.  

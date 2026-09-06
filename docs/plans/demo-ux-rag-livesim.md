# Plan — Demo UX + RAG + Live-sim + Notes (2026-09-05)

## Goal

Professional multi-tab demo UI (Groww-like), proper live-sim market tape, notes on watchlist add, real free-tier LLM + document/internet RAG for explanations. No mobile/Chrome extension.

## Tasks

| ID | Task | Status |
|----|------|--------|
| T0 | Plan + LLM choice docs | doing |
| T1 | `note` on watchlist_items (migration + API) | todo |
| T2 | Filing docs corpus + RAG retriever + web fallback | todo |
| T3 | Groq/Gemini LLM client (env key) | todo |
| T4 | Live-sim tape API + WS stream | todo |
| T5 | Multi-tab UI: Market / Watchlist / Attention / Alerts / Settings | todo |
| T6 | Wire note-on-add in Watchlist tab | todo |
| T7 | Tests + DEMO/API/LLM docs + changelog | todo |

## LLM recommendation (user provides key)

**Primary: [Groq](https://console.groq.com/) — `llama-3.3-70b-versatile` or `llama-3.1-8b-instant`**

- Free tier, fast, OpenAI-compatible API
- Env: `ENABLE_LLM=true`, `LLM_PROVIDER=groq`, `LLM_API_KEY=...`, `LLM_MODEL=llama-3.1-8b-instant`

**Fallback: Google Gemini** (`LLM_PROVIDER=gemini`, Gemini API key)

LLM **never** sets significance — only narrates retrieved + scored evidence.

## Architecture additions

```
data/filings/docs/*.md  →  RAG index (BM25 + keyword)
optional web snippets   →  ENABLE_WEB_RETRIEVAL
evidence + chunks       →  LLM paraphraser
live-sim state          →  /market/tape + WS /ws/tape
watchlist_items.note    →  why user added
```

# LLM + RAG setup

## Which free LLM to use (recommended)

### 1) Groq — **use this**

1. Create account: https://console.groq.com/  
2. Create an API key  
3. Put in repo `.env`:

```env
ENABLE_LLM=true
ENABLE_WEB_RETRIEVAL=true
LLM_PROVIDER=groq
LLM_API_KEY=gsk_your_key_here
LLM_MODEL=openai/gpt-oss-20b
```

Stronger (still free-tier subject to Groq limits):

```env
LLM_MODEL=openai/gpt-oss-120b
```

> Note (Sep 2026): `llama-3.1-8b-instant` / `llama-3.3-70b-versatile` were retired on the free developer tier. Prefer `openai/gpt-oss-20b`.

### 2) Google Gemini (fallback)

```env
ENABLE_LLM=true
LLM_PROVIDER=gemini
LLM_API_KEY=your_google_ai_studio_key
LLM_MODEL=gemini-2.0-flash
```

## What the LLM is allowed to do

- Narrate High attention cards from evidence + RAG (never invent numbers)
- Plan NLP watchlist intents (symbols/sectors) constrained to the catalog

## What the LLM must never do

- Set significance / severity / attention
- Invent tickers outside `allowed_symbols`
- Give buy/sell advice

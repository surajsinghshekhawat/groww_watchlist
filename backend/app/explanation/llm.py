"""Free-tier LLM clients (Groq / Gemini). Never invents numbers; narrates evidence + RAG."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.explanation.rag import RetrievedChunk, retrieve_for_symbol
from app.explanation.templates import explanation_from_evidence

logger = get_logger(__name__)


SYSTEM_PROMPT = """You are an explanation narrator for a stock watchlist attention engine.
Rules:
- Use ONLY the provided evidence JSON and retrieved document snippets.
- If user_note is present, you may acknowledge why the user added the stock — do NOT change importance.
- Do NOT invent prices, percentages, filings, or causality not present in the inputs.
- Do NOT give buy/sell advice.
- Write 2 short sentences max for a retail investor.
- If retrieval is empty, stick strictly to evidence fields.
"""


@dataclass
class ExplanationResult:
    text: str
    retrieval: list[dict[str, Any]] = field(default_factory=list)


async def _call_groq(messages: list[dict[str, str]]) -> str | None:
    if not settings.llm_api_key:
        return None
    model = settings.llm_model or "openai/gpt-oss-20b"
    # Short timeout — digest must not block login / Attention for 30s×N cards
    async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=3.0)) as client:
        res = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 220,
            },
        )
        if res.status_code >= 400:
            logger.warning("groq_error", extra={"status": res.status_code, "body": res.text[:200]})
            return None
        data = res.json()
        return data["choices"][0]["message"]["content"].strip()


async def _call_gemini(messages: list[dict[str, str]]) -> str | None:
    if not settings.llm_api_key:
        return None
    model = settings.llm_model or "gemini-2.0-flash"
    user_blob = "\n\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={settings.llm_api_key}"
    )
    async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=3.0)) as client:
        res = await client.post(
            url,
            json={"contents": [{"parts": [{"text": user_blob}]}]},
        )
        if res.status_code >= 400:
            logger.warning("gemini_error", extra={"status": res.status_code, "body": res.text[:200]})
            return None
        data = res.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError, TypeError):
            return None


def _chunks_payload(chunks: list[RetrievedChunk]) -> list[dict[str, Any]]:
    return [
        {
            "source": c.source,
            "title": c.title,
            "origin": c.origin,
            "score": round(c.score, 3),
        }
        for c in chunks
    ]


def _local_paraphrase(
    symbol: str,
    evidence: dict[str, Any],
    chunks: list[RetrievedChunk],
    template: str,
    user_note: str | None,
) -> str:
    ctx = evidence.get("context_evidence") or {}
    market = evidence.get("market_evidence") or {}
    info = evidence.get("information_evidence") or {}
    bits = [f"{symbol}:"]
    if ctx.get("stock_return") is not None:
        bits.append(f"moved {float(ctx['stock_return']) * 100:+.1f}% in-window")
    if market.get("rvol_score") is not None:
        bits.append(f"at {float(market['rvol_score']):.1f}× usual volume")
    if info.get("filing_present"):
        bits.append(f"with filing {info.get('filing_id') or 'on record'}")
    base = " ".join(bits) + "."
    if user_note:
        base += f" (Your note: {user_note[:120]})"
    if chunks:
        base += f" Context: {chunks[0].text[:160].replace(chr(10), ' ')}…"
    return f"{base} ({template})"


async def explain_with_optional_llm(
    symbol: str,
    evidence: dict[str, Any],
    *,
    user_note: str | None = None,
) -> ExplanationResult:
    template = explanation_from_evidence(symbol, evidence)
    if user_note:
        template = f"{template} You added this name noting: “{user_note[:160]}.”"
    chunks = await retrieve_for_symbol(symbol, evidence, include_web=False)
    retrieval = _chunks_payload(chunks)

    if not settings.enable_llm:
        # Keep explanation clean — UI shows retrieval chips separately
        return ExplanationResult(text=template, retrieval=retrieval)

    payload = {
        "symbol": symbol,
        "user_note": user_note,
        "evidence": evidence,
        "retrieved": [
            {"source": c.source, "title": c.title, "origin": c.origin, "text": c.text[:800]}
            for c in chunks
        ],
        "template_fallback": template,
    }
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": "Narrate this attention item:\n" + json.dumps(payload, default=str)[:6000],
        },
    ]

    import asyncio

    provider = (settings.llm_provider or "groq").lower()
    text: str | None = None
    try:
        call = _call_gemini(messages) if provider == "gemini" else _call_groq(messages)
        text = await asyncio.wait_for(call, timeout=9.0)
    except asyncio.TimeoutError:
        logger.warning("llm_timeout", extra={"provider": provider, "symbol": symbol})
    except Exception as exc:  # noqa: BLE001
        logger.warning("llm_call_failed", extra={"error": type(exc).__name__})

    if not text:
        logger.info("llm_fallback_local", extra={"provider": provider})
        text = _local_paraphrase(symbol, evidence, chunks, template, user_note)
    return ExplanationResult(text=text, retrieval=retrieval)

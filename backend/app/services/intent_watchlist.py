"""NLP intent → structured watchlist creation (LLM extracts; catalog match is deterministic)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.db.models import Instrument
from app.schemas.watchlist import WatchlistCreate, WatchlistResponse
from app.services.watchlist_service import WatchlistService, serialize_watchlist
from app.repositories.watchlists import WatchlistRepository

logger = get_logger(__name__)

_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")


@dataclass
class IntentPlan:
    watchlist_name: str
    symbols: list[str] = field(default_factory=list)
    sectors: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    rationale: str = ""
    raw_model: str = ""


INTENT_SYSTEM = """You turn a retail investor's natural-language request into a watchlist plan.
Rules:
- Output ONLY valid JSON (no markdown).
- Use ONLY NSE-style tickers from the allowed_symbols list when suggesting symbols.
- Never invent tickers that are not in allowed_symbols.
- sectors must be chosen from allowed_sectors when possible.
- If the user asks for "top stocks", "right now", "liquid names", or a count (e.g. "top 4"),
  pick that many diversified liquid names from allowed_symbols across sectors.
- If the user is vague, pick the best-fitting subset (max 8 symbols).
- watchlist_name: short human title (max 48 chars).
- rationale: one short investor-facing sentence (never mention "LLM", "heuristic", or "unavailable").
Schema:
{
  "watchlist_name": "string",
  "symbols": ["SYMBOL", ...],
  "sectors": ["Sector", ...],
  "themes": ["theme", ...],
  "rationale": "string"
}
"""


async def _catalog(session: AsyncSession) -> tuple[list[Instrument], list[str], list[str]]:
    rows = list(
        await session.scalars(
            select(Instrument).where(
                Instrument.is_active.is_(True),
                Instrument.is_index.is_(False),
            )
        )
    )
    symbols = sorted({r.symbol.upper() for r in rows})
    sectors = sorted({r.sector for r in rows if r.sector})
    return rows, symbols, sectors


_TOP_STOCK_HINTS = re.compile(
    r"\b(top|best|liquid|popular|active|hot|movers?|watch(?:list)?|session|right now|today|morning)\b",
    re.I,
)
_COUNT_HINT = re.compile(r"\b(?:top\s*)?(\d{1,2})\b")


def _parse_wanted_count(prompt: str, default: int = 5) -> int:
    m = _COUNT_HINT.search(prompt)
    if not m:
        return default
    n = int(m.group(1))
    return max(2, min(n, 8))


def _heuristic_plan(
    prompt: str,
    symbols: list[str],
    sectors: list[str],
    catalog: list[Instrument] | None = None,
) -> IntentPlan:
    """Offline fallback when LLM is off/unavailable — keyword match against catalog."""
    text = prompt.lower().strip()
    picked_symbols: list[str] = []
    picked_sectors: list[str] = []
    wanted = _parse_wanted_count(prompt, default=5)

    for sec in sectors:
        if sec.lower() in text or sec.lower().rstrip("s") in text:
            picked_sectors.append(sec)
    aliases = {
        "bank": "Banking",
        "banks": "Banking",
        "banking": "Banking",
        "private bank": "Banking",
        "it ": "IT",
        " it": "IT",
        "tech": "IT",
        "software": "IT",
        "services": "IT",
        "energy": "Energy",
        "oil": "Energy",
        "infra": "Industrials",
        "industrial": "Industrials",
        "construction": "Industrials",
    }
    for key, sec in aliases.items():
        if key in text and sec in sectors and sec not in picked_sectors:
            picked_sectors.append(sec)

    for sym in symbols:
        if re.search(rf"\b{re.escape(sym.lower())}\b", text):
            picked_symbols.append(sym)

    if catalog:
        for inst in catalog:
            name = inst.company_name.lower()
            tokens = [
                t
                for t in re.findall(r"[a-z]{4,}", name)
                if t
                not in {
                    "limited",
                    "industries",
                    "consultancy",
                    "services",
                    "state",
                    "bank",
                }
            ]
            if any(t in text for t in tokens):
                if inst.symbol.upper() not in picked_symbols:
                    picked_symbols.append(inst.symbol.upper())

    # Vague “top stocks right now / 4 names” → diversified liquid demo set
    if not picked_symbols and not picked_sectors and (
        _TOP_STOCK_HINTS.search(text) or text.isdigit() or len(text.split()) <= 6
    ):
        # Prefer a balanced cross-sector slate from the catalog
        preference = ["HDFCBANK", "RELIANCE", "TCS", "INFY", "ICICIBANK", "SBIN", "WIPRO", "LT"]
        for sym in preference:
            if sym in symbols and sym not in picked_symbols:
                picked_symbols.append(sym)
            if len(picked_symbols) >= wanted:
                break
        if catalog and len(picked_symbols) < wanted:
            for inst in catalog:
                if inst.symbol.upper() not in picked_symbols:
                    picked_symbols.append(inst.symbol.upper())
                if len(picked_symbols) >= wanted:
                    break

    name = "Intent watchlist"
    rationale = f"Suggested names from the demo catalog for: “{prompt.strip()[:80]}”."
    if picked_sectors and not picked_symbols:
        name = f"{picked_sectors[0]} focus"
        rationale = f"Sector match ({', '.join(picked_sectors)}) from your description."
    elif picked_symbols and _TOP_STOCK_HINTS.search(text) and not picked_sectors:
        name = f"Top {len(picked_symbols[:wanted])} session names"
        rationale = (
            f"Broad liquid names from the demo catalog ({wanted} requested) — "
            "not a live exchange ranking."
        )
    elif picked_symbols:
        name = "Named names"
        rationale = "Matched tickers / company names mentioned in your description."

    return IntentPlan(
        watchlist_name=name[:48],
        symbols=picked_symbols[:wanted],
        sectors=picked_sectors,
        themes=[],
        rationale=rationale,
        raw_model="heuristic",
    )


async def _call_llm_json(messages: list[dict[str, str]]) -> str | None:
    if not settings.enable_llm or not settings.llm_api_key:
        return None
    provider = (settings.llm_provider or "groq").lower()
    try:
        if provider == "gemini":
            model = settings.llm_model or "gemini-2.0-flash"
            blob = "\n\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                f"?key={settings.llm_api_key}"
            )
            async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=3.0)) as client:
                res = await client.post(url, json={"contents": [{"parts": [{"text": blob}]}]})
                if res.status_code >= 400:
                    logger.warning("intent_llm_error", extra={"status": res.status_code, "body": res.text[:200]})
                    return None
                data = res.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        model = settings.llm_model or "openai/gpt-oss-20b"
        async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=3.0)) as client:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 500,
            }
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if res.status_code >= 400:
                logger.warning(
                    "intent_llm_error",
                    extra={"status": res.status_code, "body": res.text[:240]},
                )
                return None
            return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("intent_llm_failed", extra={"error": type(exc).__name__})
        return None


def _parse_plan(
    raw: str,
    allowed_symbols: list[str],
    allowed_sectors: list[str],
    *,
    max_symbols: int = 8,
) -> IntentPlan:
    match = _JSON_BLOCK.search(raw)
    blob = match.group(0) if match else raw
    data = json.loads(blob)
    allow_s = {s.upper() for s in allowed_symbols}
    allow_sec = {s.lower(): s for s in allowed_sectors}
    symbols = []
    for s in data.get("symbols") or []:
        up = str(s).upper().strip()
        if up in allow_s and up not in symbols:
            symbols.append(up)
    sectors = []
    for s in data.get("sectors") or []:
        key = str(s).strip()
        canon = allow_sec.get(key.lower())
        if canon and canon not in sectors:
            sectors.append(canon)
    themes = [str(t)[:40] for t in (data.get("themes") or [])][:6]
    name = str(data.get("watchlist_name") or "Intent watchlist")[:48]
    rationale = str(data.get("rationale") or "")[:240]
    # Never leak planner internals into user-visible notes
    bad = ("llm unavailable", "heuristic", "catalog (llm", "matched keywords to the local")
    if any(b in rationale.lower() for b in bad):
        rationale = "Catalog-matched names for your description."
    cap = max(2, min(max_symbols, 8))
    return IntentPlan(
        watchlist_name=name,
        symbols=symbols[:cap],
        sectors=sectors,
        themes=themes,
        rationale=rationale,
        raw_model=raw[:500],
    )


async def plan_from_prompt(session: AsyncSession, prompt: str) -> IntentPlan:
    rows, symbols, sectors = await _catalog(session)
    cleaned = prompt.strip()
    if len(cleaned) < 4:
        raise AppError("INTENT_TOO_SHORT", "Describe what you want to watch in a bit more detail.", 400)

    # When the user asks for N names (e.g. "top 4"), enforce that cap end-to-end
    count_m = _COUNT_HINT.search(cleaned)
    max_symbols = _parse_wanted_count(cleaned, default=8) if count_m else 8

    messages = [
        {"role": "system", "content": INTENT_SYSTEM},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "request": cleaned,
                    "wanted_count": max_symbols if count_m else None,
                    "allowed_symbols": symbols,
                    "allowed_sectors": sectors,
                }
            ),
        },
    ]
    raw = await _call_llm_json(messages)
    if not raw:
        return _heuristic_plan(cleaned, symbols, sectors, catalog=rows)
    try:
        return _parse_plan(raw, symbols, sectors, max_symbols=max_symbols)
    except Exception:  # noqa: BLE001
        logger.warning("intent_parse_failed")
        return _heuristic_plan(cleaned, symbols, sectors, catalog=rows)


async def resolve_instruments(
    session: AsyncSession, plan: IntentPlan, *, limit: int = 8
) -> list[Instrument]:
    """Deterministic match: explicit symbols first, then sector expansion."""
    cap = max(1, min(limit, 8))
    found: dict[UUID, Instrument] = {}
    # Preserve plan.symbols order when present
    by_sym: dict[str, Instrument] = {}
    if plan.symbols:
        rows = list(
            await session.scalars(
                select(Instrument).where(
                    Instrument.symbol.in_(plan.symbols),
                    Instrument.is_active.is_(True),
                    Instrument.is_index.is_(False),
                )
            )
        )
        by_sym = {r.symbol.upper(): r for r in rows}
        for sym in plan.symbols:
            inst = by_sym.get(sym.upper())
            if inst and inst.instrument_id not in found:
                found[inst.instrument_id] = inst
            if len(found) >= cap:
                return list(found.values())

    if plan.sectors and len(found) < cap:
        rows = list(
            await session.scalars(
                select(Instrument).where(
                    Instrument.sector.in_(plan.sectors),
                    Instrument.is_active.is_(True),
                    Instrument.is_index.is_(False),
                )
            )
        )
        for r in rows:
            if len(found) >= cap:
                break
            found[r.instrument_id] = r

    # Theme / company-name soft match if still empty
    if not found and plan.themes:
        clauses = []
        for t in plan.themes:
            clauses.append(Instrument.company_name.ilike(f"%{t}%"))
            clauses.append(Instrument.industry.ilike(f"%{t}%"))
        if clauses:
            rows = list(
                await session.scalars(
                    select(Instrument)
                    .where(
                        Instrument.is_active.is_(True),
                        Instrument.is_index.is_(False),
                        or_(*clauses),
                    )
                    .limit(cap)
                )
            )
            for r in rows:
                found[r.instrument_id] = r

    return list(found.values())[:cap]


async def preview_watchlist_from_intent(
    session: AsyncSession, prompt: str
) -> dict[str, Any]:
    """Plan + catalog match only — does not create a watchlist."""
    plan = await plan_from_prompt(session, prompt)
    count_m = _COUNT_HINT.search(prompt.strip())
    limit = len(plan.symbols) if plan.symbols else (
        _parse_wanted_count(prompt, default=8) if count_m else 8
    )
    instruments = await resolve_instruments(session, plan, limit=limit)
    if not instruments:
        raise AppError(
            "NO_MATCHES",
            "Could not match that description to instruments in the demo catalog. "
            "Try mentioning Banking, IT, Energy, or a ticker like TCS / HDFCBANK.",
            422,
        )
    return {
        "proposed_name": plan.watchlist_name,
        "rationale": plan.rationale
        or "Catalog-matched names for your description.",
        "model": "llm" if plan.raw_model != "heuristic" else "heuristic",
        "symbols_requested": plan.symbols,
        "sectors_requested": plan.sectors,
        "themes": plan.themes,
        "matches": [
            {
                "instrument_id": str(i.instrument_id),
                "symbol": i.symbol,
                "company_name": i.company_name,
                "sector": i.sector,
                "industry": i.industry,
            }
            for i in instruments
        ],
    }


async def create_watchlist_from_selection(
    session: AsyncSession,
    user_id: UUID,
    *,
    name: str,
    instrument_ids: list[UUID],
    note: str | None = None,
    prompt: str | None = None,
) -> dict[str, Any]:
    """Create a new watchlist (playlist) from user-confirmed instrument ids."""
    if not instrument_ids:
        raise AppError("EMPTY_SELECTION", "Select at least one instrument.", 400)

    rows = list(
        await session.scalars(
            select(Instrument).where(
                Instrument.instrument_id.in_(instrument_ids),
                Instrument.is_active.is_(True),
                Instrument.is_index.is_(False),
            )
        )
    )
    by_id = {r.instrument_id: r for r in rows}
    ordered = [by_id[i] for i in instrument_ids if i in by_id]
    if not ordered:
        raise AppError("NO_MATCHES", "None of the selected instruments are in the catalog.", 422)

    svc = WatchlistService(session)
    created = await svc.create(user_id, WatchlistCreate(name=name.strip()[:120] or "Intent watchlist"))
    # Clean investor-facing note — never store planner diagnostics
    if note:
        cleaned = note.strip()
        bad = ("llm unavailable", "heuristic", "catalog (llm", "matched keywords to the local")
        if any(b in cleaned.lower() for b in bad):
            cleaned = ""
    else:
        cleaned = ""
    if not cleaned and prompt:
        cleaned = f"Watching: {prompt.strip()[:120]}"
    elif not cleaned:
        cleaned = "Added via describe-a-watchlist"
    item_note = cleaned[:200]
    repo = WatchlistRepository(session)
    wl = await repo.get_owned(created.watchlist_id, user_id)
    assert wl is not None
    for inst in ordered:
        await repo.add_item(watchlist=wl, instrument_id=inst.instrument_id, note=item_note)
    await session.commit()
    loaded = await repo.get_owned(created.watchlist_id, user_id)
    assert loaded is not None
    watchlist: WatchlistResponse = serialize_watchlist(loaded)
    return {
        "watchlist": watchlist.model_dump(mode="json"),
        "matched_symbols": [i.symbol for i in ordered],
    }


async def create_watchlist_from_intent(
    session: AsyncSession, user_id: UUID, prompt: str
) -> dict[str, Any]:
    """Legacy one-shot helper — prefer preview + create_watchlist_from_selection."""
    preview = await preview_watchlist_from_intent(session, prompt)
    ids = [UUID(m["instrument_id"]) for m in preview["matches"]]
    created = await create_watchlist_from_selection(
        session,
        user_id,
        name=preview["proposed_name"],
        instrument_ids=ids,
        note=preview["rationale"],
        prompt=prompt,
    )
    return {
        "watchlist": created["watchlist"],
        "plan": {
            "watchlist_name": preview["proposed_name"],
            "symbols_requested": preview["symbols_requested"],
            "sectors_requested": preview["sectors_requested"],
            "themes": preview["themes"],
            "rationale": preview["rationale"],
            "matched_symbols": created["matched_symbols"],
            "model": preview["model"],
        },
    }

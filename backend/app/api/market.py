"""Market tape endpoints — live-sim demo board or Yahoo delayed quotes."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter
from sqlalchemy import select

from app.core.config import settings
from app.db.models import Instrument
from app.db.session import AsyncSessionLocal
from app.ingestion.factory import get_market_data_provider
from app.sync.live_sim import snapshot_tape

router = APIRouter(prefix="/market", tags=["market"])

# Rough prior close cache for change% on yahoo tape (in-process)
_prev_close: dict[str, float] = {}


@router.get("/tape")
async def market_tape() -> dict:
    mode = (settings.market_data_mode or "replay").lower()
    if mode in {"yahoo", "yfinance"}:
        quotes = await _yahoo_tape_quotes()
        return {
            "mode": "yahoo",
            "label": "Delayed Yahoo Finance quotes (NSE .NS) — not a licensed exchange feed",
            "quotes": quotes,
        }
    quotes = await snapshot_tape()
    return {
        "mode": "live-sim",
        "label": "Demo market tape (simulated ticks — not a live exchange feed)",
        "quotes": quotes,
    }


async def _yahoo_tape_quotes() -> list[dict]:
    provider = get_market_data_provider()
    async with AsyncSessionLocal() as session:
        rows = list(
            await session.scalars(select(Instrument).where(Instrument.is_active.is_(True)))
        )
    by_id = {r.instrument_id: r for r in rows}
    snaps = await provider.get_snapshot(list(by_id.keys()))
    now = datetime.now(timezone.utc).isoformat()
    out: list[dict] = []
    for obs in snaps:
        inst = by_id.get(obs.instrument_id)
        if inst is None:
            continue
        price = float(obs.price)
        prev = _prev_close.get(inst.symbol)
        if prev is None or prev <= 0:
            change_pct = 0.0
            direction = "flat"
        else:
            change_pct = (price - prev) / prev * 100.0
            direction = "up" if change_pct > 0.02 else "down" if change_pct < -0.02 else "flat"
        # Seed prev on first tick so next poll shows change; use tiny noise floor
        if inst.symbol not in _prev_close:
            _prev_close[inst.symbol] = price
        else:
            # Keep a soft prior so change_pct reflects session drift across polls
            _prev_close[inst.symbol] = 0.9 * _prev_close[inst.symbol] + 0.1 * price
        out.append(
            {
                "instrument_id": str(inst.instrument_id),
                "symbol": inst.symbol,
                "price": price,
                "change_pct": round(change_pct, 3),
                "volume": float(obs.volume or Decimal("0")),
                "direction": direction,
                "updated_at": now,
                "is_index": bool(inst.is_index),
            }
        )
    out.sort(key=lambda q: (not q["is_index"], q["symbol"]))
    return out

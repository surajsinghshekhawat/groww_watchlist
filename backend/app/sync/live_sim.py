"""In-memory live-sim market tape — looks like a live board for demo."""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.ingestion.replay import ReplayMarketDataProvider
from app.seed import INSTRUMENT_IDS


@dataclass
class TapeQuote:
    instrument_id: UUID
    symbol: str
    price: float
    change_pct: float
    volume: float
    direction: str  # up | down | flat
    updated_at: str


@dataclass
class LiveSimState:
    quotes: dict[str, TapeQuote] = field(default_factory=dict)
    bases: dict[str, float] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    started: bool = False
    rng: random.Random = field(default_factory=lambda: random.Random(7))


_STATE = LiveSimState()


async def ensure_live_sim_seeded() -> None:
    if _STATE.quotes:
        return
    async with _STATE.lock:
        if _STATE.quotes:
            return
        replay = ReplayMarketDataProvider()
        now = datetime.now(timezone.utc).isoformat()
        for symbol, iid in INSTRUMENT_IDS.items():
            if symbol in {"NIFTY50", "NIFTYBANK"}:
                # include indices on tape too
                pass
            hist = await replay.get_history(
                iid,
                start=datetime(2026, 9, 4, 4, 0, tzinfo=timezone.utc),
                end=datetime(2026, 9, 4, 9, 0, tzinfo=timezone.utc),
            )
            if not hist:
                continue
            px = float(hist[-1].price)
            _STATE.bases[symbol] = px
            _STATE.bases[f"{symbol}__vol"] = float(hist[-1].volume)
            _STATE.quotes[symbol] = TapeQuote(
                instrument_id=iid,
                symbol=symbol,
                price=px,
                change_pct=0.0,
                volume=float(hist[-1].volume),
                direction="flat",
                updated_at=now,
            )
        _STATE.started = True


async def tick_live_sim() -> list[dict[str, Any]]:
    await ensure_live_sim_seeded()
    async with _STATE.lock:
        now = datetime.now(timezone.utc).isoformat()
        out: list[dict[str, Any]] = []
        for symbol, q in _STATE.quotes.items():
            # Indices quieter; names more volatile; HDFC/SBIN a bit hotter for demo story
            amp = 0.0008
            if symbol in {"HDFCBANK", "SBIN"}:
                amp = 0.0025
            elif symbol in {"NIFTY50", "NIFTYBANK"}:
                amp = 0.0004
            delta = _STATE.rng.uniform(-amp, amp)
            new_px = max(0.01, q.price * (1 + delta))
            base = _STATE.bases.get(symbol, new_px)
            chg = (new_px - base) / base * 100.0
            direction = "up" if new_px > q.price else "down" if new_px < q.price else "flat"
            # Volume: small noise around seed baseline — never compound every tick
            base_vol = float(_STATE.bases.get(f"{symbol}__vol", q.volume) or q.volume)
            if f"{symbol}__vol" not in _STATE.bases:
                _STATE.bases[f"{symbol}__vol"] = float(q.volume)
                base_vol = float(q.volume)
            vol = base_vol * (1 + _STATE.rng.uniform(-0.02, 0.02))
            updated = TapeQuote(
                instrument_id=q.instrument_id,
                symbol=symbol,
                price=round(new_px, 2),
                change_pct=round(chg, 3),
                volume=round(max(vol, 1.0), 0),
                direction=direction,
                updated_at=now,
            )
            _STATE.quotes[symbol] = updated
            out.append(
                {
                    "instrument_id": str(updated.instrument_id),
                    "symbol": updated.symbol,
                    "price": updated.price,
                    "change_pct": updated.change_pct,
                    "volume": updated.volume,
                    "direction": updated.direction,
                    "updated_at": updated.updated_at,
                    "is_index": symbol in {"NIFTY50", "NIFTYBANK"},
                }
            )
        return out


async def get_tape_quotes() -> list[dict[str, Any]]:
    """Current tape without advancing (for engine ingest)."""
    await ensure_live_sim_seeded()
    async with _STATE.lock:
        return [
            {
                "instrument_id": str(q.instrument_id),
                "symbol": q.symbol,
                "price": q.price,
                "change_pct": q.change_pct,
                "volume": q.volume,
                "direction": q.direction,
                "updated_at": q.updated_at,
                "is_index": symbol in {"NIFTY50", "NIFTYBANK"},
            }
            for symbol, q in _STATE.quotes.items()
        ]


async def snapshot_tape() -> list[dict[str, Any]]:
    await ensure_live_sim_seeded()
    # one micro-tick so UI never looks frozen
    return await tick_live_sim()


# Background ticker for WS subscribers
_subscribers: set[asyncio.Queue] = set()


async def subscribe_tape() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=8)
    _subscribers.add(q)
    return q


def unsubscribe_tape(q: asyncio.Queue) -> None:
    _subscribers.discard(q)


async def tape_broadcast_loop(interval: float = 1.0) -> None:
    while True:
        try:
            snap = await tick_live_sim()
            dead: list[asyncio.Queue] = []
            for q in list(_subscribers):
                try:
                    q.put_nowait({"type": "tape", "quotes": snap, "ts": time.time()})
                except asyncio.QueueFull:
                    try:
                        q.get_nowait()
                        q.put_nowait({"type": "tape", "quotes": snap, "ts": time.time()})
                    except Exception:  # noqa: BLE001
                        dead.append(q)
            for q in dead:
                unsubscribe_tape(q)
        except Exception:  # noqa: BLE001
            pass
        await asyncio.sleep(interval)

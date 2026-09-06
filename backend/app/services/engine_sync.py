"""Persist market ticks into Postgres; rescore infrequently.

Uses the configured MARKET_DATA_MODE provider (yahoo | live-sim | …).
Price sync keeps Prices fresh. Full detect/score runs on a longer cadence
so mark-seen is not wiped every few seconds.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import Instrument, PricePoint, Watchlist, WatchlistItem
from app.db.session import AsyncSessionLocal
from app.ingestion.corporate_actions import adjust_price, load_corporate_actions
from app.ingestion.factory import get_market_data_provider
from app.services.notification_service import notify_owners_for_event
from app.services.pipeline import score_watchlist_instruments
from app.sync.live_sim import ensure_live_sim_seeded, get_tape_quotes
from app.sync.pubsub import publish_watchlist_event

logger = get_logger(__name__)

_score_tick = 0


def _mode() -> str:
    return (settings.market_data_mode or "replay").lower()


def _uses_yahoo() -> bool:
    return _mode() in {"yahoo", "yfinance"}


def _uses_live_sim_tape() -> bool:
    """Demo path: replay/live still drive the in-process tape into the engine."""
    return not _uses_yahoo()


async def _ingest_from_provider(session) -> tuple[int, str]:
    provider = get_market_data_provider()
    ids = list(
        await session.scalars(select(Instrument.instrument_id).where(Instrument.is_active.is_(True)))
    )
    snaps = await provider.get_snapshot(ids)
    actions = load_corporate_actions()
    now = datetime.now(timezone.utc)
    n = 0
    source = "yahoo"
    for obs in snaps:
        source = obs.source
        adj = adjust_price(obs.instrument_id, obs.price, obs.timestamp, actions)
        session.add(
            PricePoint(
                instrument_id=obs.instrument_id,
                timestamp=obs.timestamp,
                price=adj,
                volume=obs.volume,
                source=obs.source,
                received_at=now,
            )
        )
        n += 1
    return n, source


async def _ingest_live_sim(session) -> tuple[int, str]:
    await ensure_live_sim_seeded()
    quotes = await get_tape_quotes()
    actions = load_corporate_actions()
    now = datetime.now(timezone.utc)
    n = 0
    for q in quotes:
        iid = UUID(q["instrument_id"])
        from decimal import Decimal

        price = Decimal(str(q["price"]))
        volume = Decimal(str(q["volume"]))
        adj = adjust_price(iid, price, now, actions)
        session.add(
            PricePoint(
                instrument_id=iid,
                timestamp=now,
                price=adj,
                volume=volume,
                source="live-sim",
                received_at=now,
            )
        )
        n += 1
    return n, "live-sim"


async def sync_tape_prices_only() -> int:
    async with AsyncSessionLocal() as session:
        if _uses_yahoo():
            n, _ = await _ingest_from_provider(session)
        else:
            n, _ = await _ingest_live_sim(session)
        await session.commit()
    return n


async def sync_tape_into_engine(*, do_score: bool) -> dict:
    results: list = []
    wl_ids: list = []
    ingested = 0
    source = "unknown"

    async with AsyncSessionLocal() as session:
        if _uses_yahoo():
            ingested, source = await _ingest_from_provider(session)
        else:
            ingested, source = await _ingest_live_sim(session)

        await session.flush()

        if do_score:
            results = await score_watchlist_instruments(session)
            for row in results:
                # Notify only on new event or severity escalation (edge G1)
                if not row.get("created") and not row.get("escalated"):
                    continue
                inst = await session.scalar(
                    select(Instrument).where(Instrument.instrument_id == row["instrument_id"])
                )
                if inst is None:
                    continue
                await notify_owners_for_event(
                    session,
                    instrument_id=row["instrument_id"],
                    event_id=row["event_id"],
                    symbol=row["symbol"],
                    severity=row["severity"],
                    company_name=inst.company_name,
                )

        wl_ids = list(
            await session.scalars(select(Watchlist.watchlist_id).join(WatchlistItem).distinct())
        )
        await session.commit()

        for wid in wl_ids:
            await publish_watchlist_event(
                str(wid),
                {
                    "reason": "tape_sync",
                    "ingested": ingested,
                    "events": len(results),
                    "scored": do_score,
                    "source": source,
                },
            )

    logger.info(
        "tape_engine_sync",
        extra={
            "ingested": ingested,
            "events": len(results),
            "scored": do_score,
            "source": source,
            "mode": _mode(),
        },
    )
    return {"ingested": ingested, "events": len(results), "source": source}


async def engine_sync_loop(interval_seconds: float | None = None, score_every: int = 8) -> None:
    """Prices every interval; full rescore every score_every cycles."""
    import asyncio

    global _score_tick
    # Yahoo: slower poll (be kind to Yahoo); live-sim: snappy demo tape
    if interval_seconds is None:
        interval_seconds = 45.0 if _uses_yahoo() else 8.0
    logger.info(
        "engine_sync_loop_started",
        extra={"interval": interval_seconds, "score_every": score_every, "mode": _mode()},
    )
    while True:
        try:
            _score_tick += 1
            do_score = _score_tick % score_every == 0
            await sync_tape_into_engine(do_score=do_score)
        except Exception:
            logger.exception("engine_sync_loop_failed")
        await asyncio.sleep(interval_seconds)

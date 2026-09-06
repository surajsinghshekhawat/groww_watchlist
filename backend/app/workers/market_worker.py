"""Background worker: ingest → detect → score → notify → fan-out.

Run: python -m app.workers.market_worker
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.logging import configure_logging, get_logger
from app.db.models import Instrument, PricePoint, Watchlist, WatchlistItem
from app.db.session import AsyncSessionLocal
from app.ingestion.corporate_actions import adjust_price, load_corporate_actions
from app.ingestion.factory import get_market_data_provider
from app.services.notification_service import notify_owners_for_event
from app.services.pipeline import score_watchlist_instruments
from app.sync.pubsub import publish_watchlist_event

configure_logging()
logger = get_logger(__name__)


async def ingest_live_ticks(session) -> int:
    provider = get_market_data_provider()
    ids = list(await session.scalars(select(Instrument.instrument_id).where(Instrument.is_active.is_(True))))
    snaps = await provider.get_snapshot(ids)
    actions = load_corporate_actions()
    now = datetime.now(timezone.utc)
    n = 0
    for obs in snaps:
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
    return n


async def tick() -> None:
    async with AsyncSessionLocal() as session:
        ingested = await ingest_live_ticks(session)
        await session.flush()
        results = await score_watchlist_instruments(session)

        from app.db.models import Instrument

        for row in results:
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
                {"reason": "market_update", "ingested": ingested, "events": len(results)},
            )
        logger.info(
            "market_worker_tick",
            extra={"ingested": ingested, "events": len(results), "watchlists": len(wl_ids)},
        )


async def loop(interval_seconds: float = 20.0) -> None:
    logger.info("market_worker_started", extra={"interval": interval_seconds})
    while True:
        try:
            await tick()
        except Exception:
            logger.exception("market_worker_tick_failed")
        await asyncio.sleep(interval_seconds)


def main() -> None:
    asyncio.run(loop())


if __name__ == "__main__":
    main()

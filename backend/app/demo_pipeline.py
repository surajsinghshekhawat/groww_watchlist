"""Build demo MarketEvents from the replay scenario (real scoring path)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import delete

from app.core.logging import configure_logging, get_logger
from sqlalchemy import select

from app.db.models import EventEvidence, Instrument, MarketEvent, Notification, PricePoint
from app.db.session import AsyncSessionLocal
from app.ingestion.factory import get_market_data_provider
from app.seed import INSTRUMENT_IDS
from app.services.notification_service import notify_owners_for_event
from app.services.pipeline import persist_provider_history, score_watchlist_instruments

configure_logging()
logger = get_logger(__name__)


async def run_demo_pipeline() -> None:
    provider = get_market_data_provider()
    history_start = datetime(2026, 9, 4, 4, 0, tzinfo=timezone.utc)
    history_end = datetime(2026, 9, 4, 9, 0, tzinfo=timezone.utc)

    async with AsyncSessionLocal() as session:
        await session.execute(delete(Notification))
        await session.execute(delete(EventEvidence))
        await session.execute(delete(MarketEvent))
        await session.execute(delete(PricePoint))

        await persist_provider_history(
            session,
            provider,
            INSTRUMENT_IDS,
            history_start=history_start,
            history_end=history_end,
            received_at=datetime.now(timezone.utc),
        )
        await session.flush()

        results = await score_watchlist_instruments(session)
        for row in results:
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
        await session.commit()
        logger.info("demo_pipeline_complete", extra={"events": len(results)})


def main() -> None:
    asyncio.run(run_demo_pipeline())


if __name__ == "__main__":
    main()

"""Live provider — reads the shared live-sim tape (same ticks as Market tab)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.ingestion.base import RawObservation
from app.ingestion.replay import ReplayMarketDataProvider
from app.sync.live_sim import ensure_live_sim_seeded, get_tape_quotes


class LiveMarketDataProvider:
    """Production-shaped live interface; demo backend is the in-process live-sim tape."""

    def __init__(self) -> None:
        self._replay = ReplayMarketDataProvider()

    async def get_snapshot(self, instrument_ids: list[UUID]) -> list[RawObservation]:
        await ensure_live_sim_seeded()
        wanted = set(instrument_ids)
        quotes = await get_tape_quotes()
        now = datetime.now(timezone.utc)
        out: list[RawObservation] = []
        for q in quotes:
            iid = UUID(q["instrument_id"])
            if iid not in wanted:
                continue
            out.append(
                RawObservation(
                    instrument_id=iid,
                    timestamp=now,
                    price=Decimal(str(q["price"])),
                    volume=Decimal(str(q["volume"])),
                    source="live-sim",
                )
            )
        return out

    async def get_history(
        self,
        instrument_id: UUID,
        *,
        start: datetime,
        end: datetime,
    ) -> list[RawObservation]:
        return await self._replay.get_history(instrument_id, start=start, end=end)

"""Mock provider for unit tests / offline ticks."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.ingestion.base import RawObservation


class MockMarketDataProvider:
    def __init__(self, observations: list[RawObservation] | None = None) -> None:
        self._observations = observations or []

    async def get_snapshot(self, instrument_ids: list[UUID]) -> list[RawObservation]:
        wanted = set(instrument_ids)
        latest: dict[UUID, RawObservation] = {}
        for obs in self._observations:
            if obs.instrument_id in wanted:
                latest[obs.instrument_id] = obs
        return list(latest.values())

    async def get_history(
        self,
        instrument_id: UUID,
        *,
        start: datetime,
        end: datetime,
    ) -> list[RawObservation]:
        return [
            o
            for o in self._observations
            if o.instrument_id == instrument_id and start <= o.timestamp <= end
        ]

    def push(
        self,
        *,
        instrument_id: UUID,
        price: Decimal,
        volume: Decimal,
        timestamp: datetime | None = None,
        source: str = "mock",
    ) -> None:
        self._observations.append(
            RawObservation(
                instrument_id=instrument_id,
                timestamp=timestamp or datetime.now(timezone.utc),
                price=price,
                volume=volume,
                source=source,
            )
        )

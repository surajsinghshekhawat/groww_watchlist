"""Market data provider protocol and implementations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class RawObservation:
    instrument_id: UUID
    timestamp: datetime
    price: Decimal
    volume: Decimal
    source: str


class MarketDataProvider(Protocol):
    async def get_snapshot(self, instrument_ids: list[UUID]) -> list[RawObservation]: ...

    async def get_history(
        self,
        instrument_id: UUID,
        *,
        start: datetime,
        end: datetime,
    ) -> list[RawObservation]: ...

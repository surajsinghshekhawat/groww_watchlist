"""Deterministic replay provider — same pipeline path as live."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from app.ingestion.base import RawObservation
from app.ingestion.normalizer import validate_observation
from app.seed import INSTRUMENT_IDS


class ReplayMarketDataProvider:
    def __init__(self, replay_path: Path | None = None) -> None:
        root = Path(__file__).resolve().parents[3]
        self.replay_path = replay_path or (root / "data" / "replay" / "demo_session.json")
        self._cache: list[RawObservation] | None = None

    def _load(self) -> list[RawObservation]:
        if self._cache is not None:
            return self._cache
        if not self.replay_path.exists():
            self._cache = []
            return self._cache

        raw = json.loads(self.replay_path.read_text(encoding="utf-8"))
        rows: list[RawObservation] = []
        for item in raw:
            symbol = item["symbol"]
            instrument_id = INSTRUMENT_IDS[symbol]
            obs = RawObservation(
                instrument_id=instrument_id,
                timestamp=datetime.fromisoformat(item["timestamp"]).astimezone(timezone.utc),
                price=Decimal(str(item["price"])),
                volume=Decimal(str(item["volume"])),
                source=item.get("source", "replay"),
            )
            rows.append(validate_observation(obs, now=obs.timestamp))
        self._cache = sorted(rows, key=lambda r: r.timestamp)
        return self._cache

    async def get_snapshot(self, instrument_ids: list[UUID]) -> list[RawObservation]:
        wanted = set(instrument_ids)
        latest: dict[UUID, RawObservation] = {}
        for obs in self._load():
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
            obs
            for obs in self._load()
            if obs.instrument_id == instrument_id and start <= obs.timestamp <= end
        ]

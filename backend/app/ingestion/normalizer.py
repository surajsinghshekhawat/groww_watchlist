"""Validate and normalize raw market observations before detectors."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.ingestion.base import RawObservation


class NormalizationError(ValueError):
    pass


def validate_observation(
    obs: RawObservation,
    *,
    now: datetime | None = None,
    max_future_skew: timedelta = timedelta(minutes=2),
) -> RawObservation:
    now = now or datetime.now(timezone.utc)
    if obs.timestamp.tzinfo is None:
        raise NormalizationError("timestamp must be timezone-aware")
    if obs.timestamp - now > max_future_skew:
        raise NormalizationError("timestamp too far in the future")

    price = obs.price if isinstance(obs.price, Decimal) else Decimal(str(obs.price))
    volume = obs.volume if isinstance(obs.volume, Decimal) else Decimal(str(obs.volume))

    if price <= 0:
        raise NormalizationError("price must be positive")
    if volume < 0:
        raise NormalizationError("volume must be non-negative")
    if not obs.source.strip():
        raise NormalizationError("source is required")

    return RawObservation(
        instrument_id=obs.instrument_id,
        timestamp=obs.timestamp,
        price=price,
        volume=volume,
        source=obs.source.strip(),
    )

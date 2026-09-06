"""Event deduplication — one underlying move, one evolving MarketEvent."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EventStatus, EventType, MarketEvent


async def find_open_event(
    session: AsyncSession,
    *,
    instrument_id: UUID,
    event_type: EventType | None = None,
    around: datetime | None = None,
    window: timedelta = timedelta(days=7),
) -> MarketEvent | None:
    """Find an open/escalated event for the same instrument.

    Prefer same event_type when provided, but never create a second open card
    for the same name just because the type or clock window drifted (demo replay
    vs live-sim timestamps).
    """
    base = (
        select(MarketEvent)
        .where(
            MarketEvent.instrument_id == instrument_id,
            MarketEvent.status.in_([EventStatus.OPEN, EventStatus.ESCALATED]),
        )
        .order_by(MarketEvent.detected_at.desc())
    )

    if event_type is not None:
        same_type = await session.scalar(base.where(MarketEvent.event_type == event_type).limit(1))
        if same_type is not None:
            if around is None:
                return same_type
            # Prefer type match even across long gaps (demo day → live-sim now)
            return same_type

    any_open = await session.scalar(base.limit(1))
    if any_open is None:
        return None

    if around is not None and any_open.window_end is not None:
        # Soft window: still reuse if within `window` of the new observation
        if any_open.window_end < around - window and any_open.window_end < around:
            # Stale open event far in the past — still reuse rather than duplicate UI
            return any_open
    return any_open


async def resolve_duplicate_open_events(
    session: AsyncSession,
    *,
    instrument_id: UUID,
    keep_event_id: UUID,
) -> int:
    """Resolve other open/escalated events for this instrument (dedupe cleanup)."""
    rows = list(
        await session.scalars(
            select(MarketEvent).where(
                MarketEvent.instrument_id == instrument_id,
                MarketEvent.status.in_([EventStatus.OPEN, EventStatus.ESCALATED]),
                MarketEvent.event_id != keep_event_id,
            )
        )
    )
    for ev in rows:
        ev.status = EventStatus.RESOLVED
    return len(rows)

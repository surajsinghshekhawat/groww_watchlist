"""Event persistence helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import EventEvidence, EventStatus, EventType, MarketEvent, Severity
from app.events.deduplication import find_open_event, resolve_duplicate_open_events
from app.events.escalation import apply_escalation
from app.scoring.evidence_fusion import fuse_evidence


async def upsert_event_from_evidence(
    session: AsyncSession,
    *,
    instrument_id: UUID,
    event_type: EventType,
    evidence: dict[str, Any],
    window_start: datetime,
    window_end: datetime,
    strongest_horizon: str | None = None,
) -> tuple[MarketEvent, dict[str, bool]]:
    """Upsert open event. Returns (event, {created, escalated})."""
    severity = fuse_evidence(evidence)
    existing = await find_open_event(
        session,
        instrument_id=instrument_id,
        event_type=event_type,
        around=window_end,
    )

    if existing is None:
        event = MarketEvent(
            event_id=uuid4(),
            instrument_id=instrument_id,
            event_type=event_type,
            detected_at=window_end,
            window_start=window_start,
            window_end=window_end,
            severity=severity,
            status=EventStatus.OPEN,
            version=1,
            strongest_horizon=strongest_horizon,
        )
        session.add(event)
        session.add(EventEvidence(event_id=event.event_id, bundle=evidence))
        await session.flush()
        await resolve_duplicate_open_events(
            session, instrument_id=instrument_id, keep_event_id=event.event_id
        )
        return event, {"created": True, "escalated": False}

    event = await session.scalar(
        select(MarketEvent)
        .where(MarketEvent.event_id == existing.event_id)
        .options(selectinload(MarketEvent.evidence))
    )
    assert event is not None

    # Prefer richer type (filing over pure price move) when merging
    if event_type == EventType.FILING and event.event_type != EventType.FILING:
        event.event_type = EventType.FILING

    escalated = apply_escalation(event, new_severity=severity, new_evidence=evidence)
    event.window_end = window_end
    if strongest_horizon:
        event.strongest_horizon = strongest_horizon
    await session.flush()
    await resolve_duplicate_open_events(
        session, instrument_id=instrument_id, keep_event_id=event.event_id
    )
    return event, {"created": False, "escalated": bool(escalated)}

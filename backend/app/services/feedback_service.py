"""Persist and query attention feedback labels."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.db.models import MarketEvent, Watchlist
from app.db.models.event_feedback import EventFeedback, FeedbackLabel
from app.schemas.digest import MarkSeenItem, MarkSeenRequest


async def upsert_event_feedback(
    session: AsyncSession,
    *,
    user_id: UUID,
    event_id: UUID,
    label: str,
    watchlist_id: UUID | None = None,
    mark_away: bool = True,
) -> dict:
    try:
        parsed = FeedbackLabel(label)
    except ValueError as exc:
        raise AppError(
            "INVALID_FEEDBACK",
            "label must be useful, noise, or already_knew",
            400,
        ) from exc

    event = await session.scalar(select(MarketEvent).where(MarketEvent.event_id == event_id))
    if event is None:
        raise AppError("NOT_FOUND", "Event not found", 404)

    if watchlist_id is not None:
        owned = await session.scalar(
            select(Watchlist).where(
                Watchlist.watchlist_id == watchlist_id,
                Watchlist.user_id == user_id,
            )
        )
        if owned is None:
            raise AppError("NOT_FOUND", "Watchlist not found", 404)

    existing = await session.scalar(
        select(EventFeedback).where(
            EventFeedback.user_id == user_id,
            EventFeedback.event_id == event_id,
        )
    )
    if existing:
        existing.label = parsed
        existing.event_version = event.version
        if watchlist_id is not None:
            existing.watchlist_id = watchlist_id
        row = existing
    else:
        row = EventFeedback(
            user_id=user_id,
            event_id=event_id,
            watchlist_id=watchlist_id,
            label=parsed,
            event_version=event.version,
        )
        session.add(row)

    await session.flush()

    # Noise / already knew → leave the Attention feed (same as mark-seen)
    cleared = False
    if mark_away and parsed in {FeedbackLabel.NOISE, FeedbackLabel.ALREADY_KNEW} and watchlist_id:
        from app.services.digest_service import DigestService

        await DigestService(session).mark_seen(
            user_id,
            watchlist_id,
            MarkSeenRequest(
                items=[
                    MarkSeenItem(
                        event_id=event.event_id,
                        severity_seen=event.severity.value,
                        event_version=event.version,
                    )
                ]
            ),
        )
        cleared = True
    else:
        await session.commit()

    await session.refresh(row)
    return {
        "feedback_id": str(row.feedback_id),
        "event_id": str(row.event_id),
        "label": row.label.value,
        "event_version": row.event_version,
        "cleared_from_digest": cleared,
    }


async def feedback_by_events(
    session: AsyncSession, *, user_id: UUID, event_ids: list[UUID]
) -> dict[UUID, FeedbackLabel]:
    if not event_ids:
        return {}
    rows = list(
        await session.scalars(
            select(EventFeedback).where(
                EventFeedback.user_id == user_id,
                EventFeedback.event_id.in_(event_ids),
            )
        )
    )
    return {r.event_id: r.label for r in rows}

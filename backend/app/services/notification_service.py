"""In-app notifications for HIGH / sensitivity-gated events."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Notification, Severity, User
from app.services.pipeline import severity_meets_sensitivity, watchlists_for_instrument
from app.sync.pubsub import publish_watchlist_event


async def notify_owners_for_event(
    session: AsyncSession,
    *,
    instrument_id: UUID,
    event_id: UUID,
    symbol: str,
    severity: Severity,
    company_name: str,
) -> int:
    """Create alerts only for new / escalated attention — not every rescore (edge G1)."""
    _rank = {
        Severity.LOW: 0,
        Severity.NOTABLE: 1,
        Severity.WORTH_WATCHING: 2,
        Severity.HIGH: 3,
    }
    watchlists = await watchlists_for_instrument(session, instrument_id)
    created = 0
    for wl in watchlists:
        user = await session.scalar(select(User).where(User.user_id == wl.user_id))
        if user is None:
            continue
        sens = user.sensitivity.value if hasattr(user.sensitivity, "value") else str(user.sensitivity)
        if not severity_meets_sensitivity(severity, sens):
            continue

        # Any prior notification for this event (read or unread)
        prior = await session.scalar(
            select(Notification)
            .where(
                Notification.user_id == user.user_id,
                Notification.event_id == event_id,
            )
            .order_by(Notification.created_at.desc())
            .limit(1)
        )
        if prior is not None:
            prior_sev = prior.severity if isinstance(prior.severity, Severity) else Severity(str(prior.severity))
            if _rank.get(severity, 0) <= _rank.get(prior_sev, 0):
                continue
            # Severity rose — close the old unread twin if any
            if prior.read_at is None:
                prior.read_at = datetime.now(timezone.utc)

        unread = await session.scalar(
            select(Notification).where(
                Notification.user_id == user.user_id,
                Notification.event_id == event_id,
                Notification.read_at.is_(None),
            )
        )
        if unread:
            continue

        title = f"{symbol}: {severity.value} attention"
        body = f"{company_name} crossed your attention threshold while you were away."
        note = Notification(
            notification_id=uuid4(),
            user_id=user.user_id,
            watchlist_id=wl.watchlist_id,
            event_id=event_id,
            title=title,
            body=body,
            severity=severity,
        )
        session.add(note)
        created += 1
        try:
            from app.services import push_service

            await push_service.send_to_user(
                session,
                user.user_id,
                title=title,
                body=body,
                data={
                    "event_id": str(event_id),
                    "symbol": symbol,
                    "severity": severity.value,
                    "watchlist_id": str(wl.watchlist_id),
                },
            )
        except Exception:  # noqa: BLE001
            pass
        await publish_watchlist_event(
            str(wl.watchlist_id),
            {
                "kind": "notification",
                "title": title,
                "body": body,
                "severity": severity.value,
                "event_id": str(event_id),
            },
        )
    return created


async def list_notifications(
    session: AsyncSession,
    user_id: UUID,
    *,
    unread_only: bool = False,
    respect_sensitivity: bool = True,
):
    q = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
    )
    if unread_only:
        q = q.where(Notification.read_at.is_(None))
    rows = list(await session.scalars(q.limit(80)))

    if not respect_sensitivity:
        return rows[:50]

    user = await session.scalar(select(User).where(User.user_id == user_id))
    sens = "MEDIUM"
    if user is not None and getattr(user, "sensitivity", None) is not None:
        sens = user.sensitivity.value if hasattr(user.sensitivity, "value") else str(user.sensitivity)

    filtered: list[Notification] = []
    for r in rows:
        sev = r.severity if isinstance(r.severity, Severity) else Severity(str(r.severity))
        if severity_meets_sensitivity(sev, sens):
            filtered.append(r)
    return filtered[:50]


async def mark_notifications_read(
    session: AsyncSession, user_id: UUID, notification_ids: list[UUID] | None = None
) -> int:
    q = select(Notification).where(
        Notification.user_id == user_id,
        Notification.read_at.is_(None),
    )
    rows = list(await session.scalars(q))
    now = datetime.now(timezone.utc)
    n = 0
    for row in rows:
        if notification_ids is not None and row.notification_id not in notification_ids:
            continue
        row.read_at = now
        n += 1
    await session.commit()
    return n


async def mark_notifications_read_for_events(
    session: AsyncSession,
    user_id: UUID,
    event_ids: list[UUID],
    *,
    commit: bool = True,
) -> int:
    if not event_ids:
        return 0
    now = datetime.now(timezone.utc)
    result = await session.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.event_id.in_(event_ids),
            Notification.read_at.is_(None),
        )
        .values(read_at=now)
    )
    if commit:
        await session.commit()
    return int(result.rowcount or 0)

"""Web Push delivery via VAPID (works when the tab is closed; browser may still be running)."""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import PushSubscription

logger = get_logger(__name__)


def push_configured() -> bool:
    """True when VAPID keys are available (settings and/or process env)."""
    import os

    pub = (settings.vapid_public_key or os.getenv("VAPID_PUBLIC_KEY") or "").strip()
    priv = (settings.vapid_private_key or os.getenv("VAPID_PRIVATE_KEY") or "").strip()
    enabled = settings.enable_web_push
    if os.getenv("ENABLE_WEB_PUSH", "").lower() in {"0", "false", "no"}:
        enabled = False
    return bool(enabled and pub and priv)


async def upsert_subscription(
    session: AsyncSession,
    *,
    user_id: UUID,
    endpoint: str,
    p256dh: str,
    auth: str,
    user_agent: str | None,
) -> PushSubscription:
    existing = await session.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    )
    if existing:
        existing.user_id = user_id
        existing.p256dh = p256dh
        existing.auth = auth
        existing.user_agent = user_agent
        await session.commit()
        await session.refresh(existing)
        return existing
    row = PushSubscription(
        user_id=user_id,
        endpoint=endpoint,
        p256dh=p256dh,
        auth=auth,
        user_agent=user_agent,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def delete_subscription(session: AsyncSession, *, user_id: UUID, endpoint: str) -> bool:
    row = await session.scalar(
        select(PushSubscription).where(
            PushSubscription.user_id == user_id,
            PushSubscription.endpoint == endpoint,
        )
    )
    if row is None:
        return False
    await session.delete(row)
    await session.commit()
    return True


async def list_for_user(session: AsyncSession, user_id: UUID) -> list[PushSubscription]:
    return list(
        await session.scalars(
            select(PushSubscription).where(PushSubscription.user_id == user_id)
        )
    )


def _send_one(sub: PushSubscription, *, title: str, body: str, data: dict) -> bool:
    if not push_configured():
        return False
    try:
        from pywebpush import WebPushException, webpush

        webpush(
            subscription_info={
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
            },
            data=json.dumps(
                {
                    "title": title,
                    "body": body,
                    "data": data,
                }
            ),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
            vapid_public_key=settings.vapid_public_key,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        # ImportError if pywebpush missing, WebPushException if gone/expired
        logger.warning(
            "web_push_failed",
            extra={"error": type(exc).__name__, "endpoint": sub.endpoint[:48]},
        )
        return False


async def send_to_user(
    session: AsyncSession,
    user_id: UUID,
    *,
    title: str,
    body: str,
    data: dict | None = None,
) -> int:
    if not push_configured():
        return 0
    subs = await list_for_user(session, user_id)
    sent = 0
    stale: list[PushSubscription] = []
    payload = data or {}
    for sub in subs:
        ok = _send_one(sub, title=title, body=body, data=payload)
        if ok:
            sent += 1
        else:
            # Drop dead endpoints so we don't keep failing
            try:
                from pywebpush import WebPushException  # noqa: F401
            except ImportError:
                break
            stale.append(sub)
    for sub in stale:
        # Conservative: only delete on clear gone responses is hard without exception detail;
        # leave subscriptions; next successful subscribe refreshes.
        pass
    return sent

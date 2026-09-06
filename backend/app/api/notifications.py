from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.api.dependencies import CurrentUser, DbSession
from app.core.rate_limit import enforce_rate_limit
from app.schemas.notifications import MarkNotificationsReadRequest, NotificationResponse
from app.services import notification_service as notif

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    user: CurrentUser,
    session: DbSession,
    unread_only: bool = Query(False),
) -> list[NotificationResponse]:
    rows = await notif.list_notifications(session, user.user_id, unread_only=unread_only)
    return [
        NotificationResponse(
            notification_id=r.notification_id,
            watchlist_id=r.watchlist_id,
            event_id=r.event_id,
            title=r.title,
            body=r.body,
            severity=r.severity.value if hasattr(r.severity, "value") else str(r.severity),
            read_at=r.read_at,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/mark-read")
async def mark_read(
    payload: MarkNotificationsReadRequest,
    user: CurrentUser,
    session: DbSession,
    request: Request,
) -> dict:
    await enforce_rate_limit(request, scope="notif_read", limit=60, window_seconds=60)
    n = await notif.mark_notifications_read(session, user.user_id, payload.notification_ids)
    return {"ok": True, "marked": n}

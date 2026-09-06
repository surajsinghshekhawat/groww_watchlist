"""Web Push subscribe / unsubscribe APIs."""

from fastapi import APIRouter, Request

from app.api.dependencies import CurrentUser, DbSession
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.rate_limit import enforce_rate_limit
from app.schemas.push import PushStatusResponse, PushSubscribeRequest, PushUnsubscribeRequest
from app.services import push_service

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/vapid-public-key")
async def vapid_public_key() -> dict:
    import os

    if not push_service.push_configured():
        raise AppError(
            "PUSH_NOT_CONFIGURED",
            "Web Push is not configured. Set VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY.",
            503,
        )
    pub = (settings.vapid_public_key or os.getenv("VAPID_PUBLIC_KEY") or "").strip()
    return {"public_key": pub, "configured": True}


@router.get("/status", response_model=PushStatusResponse)
async def push_status(user: CurrentUser, session: DbSession) -> PushStatusResponse:
    rows = await push_service.list_for_user(session, user.user_id)
    return PushStatusResponse(
        configured=push_service.push_configured(),
        subscribed=len(rows) > 0,
        subscription_count=len(rows),
    )


@router.post("/subscribe")
async def subscribe(
    payload: PushSubscribeRequest,
    user: CurrentUser,
    session: DbSession,
    request: Request,
) -> dict:
    await enforce_rate_limit(request, scope="push_subscribe", limit=20, window_seconds=60)
    if not push_service.push_configured():
        raise AppError("PUSH_NOT_CONFIGURED", "Web Push is not configured on the server", 503)
    ua = request.headers.get("user-agent")
    row = await push_service.upsert_subscription(
        session,
        user_id=user.user_id,
        endpoint=payload.endpoint,
        p256dh=payload.keys.p256dh,
        auth=payload.keys.auth,
        user_agent=ua,
    )
    return {"ok": True, "subscription_id": str(row.subscription_id)}


@router.post("/unsubscribe")
async def unsubscribe(
    payload: PushUnsubscribeRequest,
    user: CurrentUser,
    session: DbSession,
    request: Request,
) -> dict:
    await enforce_rate_limit(request, scope="push_unsub", limit=20, window_seconds=60)
    ok = await push_service.delete_subscription(
        session, user_id=user.user_id, endpoint=payload.endpoint
    )
    return {"ok": ok}

from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.api.dependencies import CurrentUser, DbSession
from app.core.rate_limit import enforce_rate_limit
from app.schemas.digest import DigestResponse, MarkSeenRequest
from app.services.digest_service import DigestService

router = APIRouter(tags=["digest"])


@router.get("/watchlists/{watchlist_id}/digest", response_model=DigestResponse)
async def get_digest(
    watchlist_id: UUID,
    user: CurrentUser,
    session: DbSession,
    request: Request,
    top_k: int = Query(5, ge=1, le=20),
) -> DigestResponse:
    await enforce_rate_limit(request, scope="digest", limit=60, window_seconds=60)
    return await DigestService(session).get_digest(user.user_id, watchlist_id, top_k=top_k)


@router.post("/watchlists/{watchlist_id}/mark-seen")
async def mark_seen(
    watchlist_id: UUID,
    payload: MarkSeenRequest,
    user: CurrentUser,
    session: DbSession,
    request: Request,
) -> dict:
    await enforce_rate_limit(request, scope="mark_seen", limit=60, window_seconds=60)
    return await DigestService(session).mark_seen(user.user_id, watchlist_id, payload)


@router.post("/watchlists/{watchlist_id}/reset-seen")
async def reset_seen(
    watchlist_id: UUID,
    user: CurrentUser,
    session: DbSession,
    request: Request,
) -> dict:
    """Clear mark-seen state for this watchlist (demo / catch-up reset)."""
    await enforce_rate_limit(request, scope="reset_seen", limit=20, window_seconds=60)
    return await DigestService(session).reset_seen(user.user_id, watchlist_id)


@router.post("/watchlists/{watchlist_id}/touch-checked")
async def touch_checked(
    watchlist_id: UUID,
    user: CurrentUser,
    session: DbSession,
    request: Request,
) -> dict:
    """Stamp last_checked_at = now when the user opens Attention."""
    await enforce_rate_limit(request, scope="touch_checked", limit=30, window_seconds=60)
    return await DigestService(session).touch_checked(user.user_id, watchlist_id)

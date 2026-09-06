"""Attention feedback API — useful / noise / already_knew."""

from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.api.dependencies import CurrentUser, DbSession
from app.core.rate_limit import enforce_rate_limit
from app.services import feedback_service

router = APIRouter(tags=["feedback"])


class FeedbackRequest(BaseModel):
    label: str = Field(..., description="useful | noise | already_knew")
    watchlist_id: UUID | None = None


@router.post("/events/{event_id}/feedback")
async def post_event_feedback(
    event_id: UUID,
    payload: FeedbackRequest,
    user: CurrentUser,
    session: DbSession,
    request: Request,
) -> dict:
    await enforce_rate_limit(request, scope="feedback", limit=60, window_seconds=60)
    return await feedback_service.upsert_event_feedback(
        session,
        user_id=user.user_id,
        event_id=event_id,
        label=payload.label.strip().lower(),
        watchlist_id=payload.watchlist_id,
    )

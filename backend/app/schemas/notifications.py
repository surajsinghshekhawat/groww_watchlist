from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    notification_id: UUID
    watchlist_id: UUID | None
    event_id: UUID | None
    title: str
    body: str
    severity: str
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MarkNotificationsReadRequest(BaseModel):
    notification_ids: list[UUID] | None = Field(
        default=None, description="Omit to mark all unread as read"
    )

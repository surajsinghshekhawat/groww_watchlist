"""User feedback on attention events — useful / noise / already_knew."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FeedbackLabel(str, enum.Enum):
    USEFUL = "useful"
    NOISE = "noise"
    ALREADY_KNEW = "already_knew"


class EventFeedback(Base):
    """Per-user label on an event version — honest labels where public ground truth is missing."""

    __tablename__ = "event_feedback"
    __table_args__ = (
        UniqueConstraint("user_id", "event_id", name="uq_event_feedback_user_event"),
        Index("ix_event_feedback_user_created", "user_id", "created_at"),
    )

    feedback_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("market_events.event_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    watchlist_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("watchlists.watchlist_id", ondelete="SET NULL"),
        nullable=True,
    )
    label: Mapped[FeedbackLabel] = mapped_column(
        Enum(
            FeedbackLabel,
            name="feedback_label",
            values_callable=lambda e: [x.value for x in e],
        ),
        nullable=False,
    )
    event_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

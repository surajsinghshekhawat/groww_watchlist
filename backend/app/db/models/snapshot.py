import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WatchlistSnapshot(Base):
    """Per-user per-instrument memory for event-state-aware novelty."""

    __tablename__ = "watchlist_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "instrument_id", name="uq_snapshot_user_instrument"),
    )

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instruments.instrument_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    # { eventId: { eventId, severitySeen, eventVersion, seenAt } }
    last_seen_event_states: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="snapshots")
    instrument = relationship("Instrument")

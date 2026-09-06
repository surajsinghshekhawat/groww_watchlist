import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EventType(str, enum.Enum):
    PRICE_ANOMALY = "PRICE_ANOMALY"
    VOLUME_ANOMALY = "VOLUME_ANOMALY"
    CONTEXT_DIVERGENCE = "CONTEXT_DIVERGENCE"
    CHANGE_POINT = "CHANGE_POINT"
    CORPORATE_ACTION = "CORPORATE_ACTION"
    FILING = "FILING"
    EARNINGS = "EARNINGS"


class Severity(str, enum.Enum):
    LOW = "LOW"
    NOTABLE = "NOTABLE"
    WORTH_WATCHING = "WORTH_WATCHING"
    HIGH = "HIGH"


class EventStatus(str, enum.Enum):
    OPEN = "OPEN"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"


class MarketEvent(Base):
    """First-class market event — Detection → Event → Evidence → Score."""

    __tablename__ = "market_events"
    __table_args__ = (
        Index("ix_market_events_instrument_detected", "instrument_id", "detected_at"),
        Index("ix_market_events_status_detected", "status", "detected_at"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instruments.instrument_id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, name="event_type"), nullable=False
    )
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity"), nullable=False, default=Severity.LOW
    )
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, name="event_status"), nullable=False, default=EventStatus.OPEN
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    strongest_horizon: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    instrument = relationship("Instrument", back_populates="market_events")
    evidence = relationship(
        "EventEvidence",
        back_populates="event",
        uselist=False,
        cascade="all, delete-orphan",
    )


class EventEvidence(Base):
    """Structured evidence bundle — machine-readable, not an opaque score."""

    __tablename__ = "event_evidence"

    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("market_events.event_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Groups: market_evidence, context_evidence, persistence_evidence, information_evidence
    bundle: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    event = relationship("MarketEvent", back_populates="evidence")

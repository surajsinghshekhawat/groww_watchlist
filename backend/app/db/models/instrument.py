import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Exchange(str, enum.Enum):
    NSE = "NSE"
    BSE = "BSE"


class TradingCategory(str, enum.Enum):
    NORMAL = "NORMAL"
    TRADE_FOR_TRADE = "TRADE_FOR_TRADE"
    ASM = "ASM"
    GSM = "GSM"


class Instrument(Base):
    """Stable instrument identity — never use ticker symbol as the permanent key."""

    __tablename__ = "instruments"
    __table_args__ = (
        UniqueConstraint("symbol", "exchange", name="uq_instruments_symbol_exchange"),
    )

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    exchange: Mapped[Exchange] = mapped_column(Enum(Exchange, name="exchange"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    sector: Mapped[str] = mapped_column(String(100), nullable=False)
    industry: Mapped[str] = mapped_column(String(120), nullable=False)
    beta_vs_market: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=1)
    beta_vs_sector: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=1)
    trading_category: Mapped[TradingCategory] = mapped_column(
        Enum(TradingCategory, name="trading_category"),
        nullable=False,
        default=TradingCategory.NORMAL,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_index: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    watchlist_items = relationship("WatchlistItem", back_populates="instrument")
    price_points = relationship("PricePoint", back_populates="instrument")
    market_events = relationship("MarketEvent", back_populates="instrument")

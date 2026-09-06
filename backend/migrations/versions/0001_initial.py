"""Initial schema: users, instruments, watchlists, prices, events, snapshots.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    exchange = postgresql.ENUM("NSE", "BSE", name="exchange", create_type=False)
    trading_category = postgresql.ENUM(
        "NORMAL", "TRADE_FOR_TRADE", "ASM", "GSM", name="trading_category", create_type=False
    )
    event_type = postgresql.ENUM(
        "PRICE_ANOMALY",
        "VOLUME_ANOMALY",
        "CONTEXT_DIVERGENCE",
        "CHANGE_POINT",
        "CORPORATE_ACTION",
        "FILING",
        "EARNINGS",
        name="event_type",
        create_type=False,
    )
    severity = postgresql.ENUM(
        "LOW", "NOTABLE", "WORTH_WATCHING", "HIGH", name="severity", create_type=False
    )
    event_status = postgresql.ENUM(
        "OPEN", "ESCALATED", "RESOLVED", name="event_status", create_type=False
    )

    exchange.create(op.get_bind(), checkfirst=True)
    trading_category.create(op.get_bind(), checkfirst=True)
    event_type.create(op.get_bind(), checkfirst=True)
    severity.create(op.get_bind(), checkfirst=True)
    event_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "instruments",
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("exchange", exchange, nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sector", sa.String(length=100), nullable=False),
        sa.Column("industry", sa.String(length=120), nullable=False),
        sa.Column("beta_vs_market", sa.Numeric(8, 4), nullable=False),
        sa.Column("beta_vs_sector", sa.Numeric(8, 4), nullable=False),
        sa.Column("trading_category", trading_category, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_index", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("symbol", "exchange", name="uq_instruments_symbol_exchange"),
    )
    op.create_index("ix_instruments_symbol", "instruments", ["symbol"])
    op.create_index("ix_instruments_company_id", "instruments", ["company_id"])

    op.create_table(
        "watchlists",
        sa.Column("watchlist_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_watchlists_user_id", "watchlists", ["user_id"])

    op.create_table(
        "watchlist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("watchlist_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("watchlists.watchlist_id", ondelete="CASCADE"), nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.instrument_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("watchlist_id", "instrument_id", name="uq_watchlist_instrument"),
    )
    op.create_index("ix_watchlist_items_watchlist_id", "watchlist_items", ["watchlist_id"])
    op.create_index("ix_watchlist_items_instrument_id", "watchlist_items", ["instrument_id"])

    op.create_table(
        "price_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.instrument_id", ondelete="CASCADE"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price", sa.Numeric(18, 6), nullable=False),
        sa.Column("volume", sa.Numeric(20, 4), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("price > 0", name="ck_price_points_price_positive"),
        sa.CheckConstraint("volume >= 0", name="ck_price_points_volume_nonneg"),
    )
    op.create_index("ix_price_points_instrument_timestamp", "price_points", ["instrument_id", "timestamp"])

    op.create_table(
        "market_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.instrument_id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", event_type, nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", severity, nullable=False),
        sa.Column("status", event_status, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("strongest_horizon", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_market_events_instrument_detected", "market_events", ["instrument_id", "detected_at"])
    op.create_index("ix_market_events_status_detected", "market_events", ["status", "detected_at"])

    op.create_table(
        "event_evidence",
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("market_events.event_id", ondelete="CASCADE"), nullable=False),
        sa.Column("bundle", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_event_evidence_event_id", "event_evidence", ["event_id"])

    op.create_table(
        "watchlist_snapshots",
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.instrument_id", ondelete="CASCADE"), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("last_seen_event_states", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "instrument_id", name="uq_snapshot_user_instrument"),
    )
    op.create_index("ix_watchlist_snapshots_user_id", "watchlist_snapshots", ["user_id"])
    op.create_index("ix_watchlist_snapshots_instrument_id", "watchlist_snapshots", ["instrument_id"])


def downgrade() -> None:
    op.drop_table("watchlist_snapshots")
    op.drop_table("event_evidence")
    op.drop_table("market_events")
    op.drop_table("price_points")
    op.drop_table("watchlist_items")
    op.drop_table("watchlists")
    op.drop_table("instruments")
    op.drop_table("users")

    sa.Enum(name="event_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="severity").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="event_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="trading_category").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="exchange").drop(op.get_bind(), checkfirst=True)

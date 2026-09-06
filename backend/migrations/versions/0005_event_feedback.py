"""Add event_feedback for useful / noise / already_knew labels.

Revision ID: 0005_event_feedback
Revises: 0004_push_subscriptions
Create Date: 2026-09-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_event_feedback"
down_revision: Union[str, None] = "0004_push_subscriptions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum once (idempotent) — table column must not recreate it
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE feedback_label AS ENUM ('useful', 'noise', 'already_knew');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )

    op.create_table(
        "event_feedback",
        sa.Column("feedback_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("market_events.event_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "watchlist_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("watchlists.watchlist_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "label",
            postgresql.ENUM(
                "useful",
                "noise",
                "already_knew",
                name="feedback_label",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("event_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "event_id", name="uq_event_feedback_user_event"),
    )
    op.create_index("ix_event_feedback_user_id", "event_feedback", ["user_id"])
    op.create_index("ix_event_feedback_event_id", "event_feedback", ["event_id"])
    op.create_index(
        "ix_event_feedback_user_created", "event_feedback", ["user_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_event_feedback_user_created", table_name="event_feedback")
    op.drop_index("ix_event_feedback_event_id", table_name="event_feedback")
    op.drop_index("ix_event_feedback_user_id", table_name="event_feedback")
    op.drop_table("event_feedback")
    op.execute("DROP TYPE IF EXISTS feedback_label")

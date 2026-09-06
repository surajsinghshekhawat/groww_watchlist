"""Add user sensitivity + notifications table.

Revision ID: 0002_notifications_sensitivity
Revises: 0001_initial
Create Date: 2026-09-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_notifications_sensitivity"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    sensitivity = postgresql.ENUM("LOW", "MEDIUM", "HIGH", name="sensitivity", create_type=False)
    sensitivity.create(bind, checkfirst=True)

    # Idempotent column add (partial failed runs)
    op.execute(
        """
        DO $$ BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='users' AND column_name='sensitivity'
          ) THEN
            ALTER TABLE users ADD COLUMN sensitivity sensitivity NOT NULL DEFAULT 'MEDIUM';
          END IF;
        END $$;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
          notification_id UUID PRIMARY KEY,
          user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
          watchlist_id UUID REFERENCES watchlists(watchlist_id) ON DELETE SET NULL,
          event_id UUID REFERENCES market_events(event_id) ON DELETE SET NULL,
          title VARCHAR(200) NOT NULL,
          body TEXT NOT NULL,
          severity severity NOT NULL,
          read_at TIMESTAMPTZ,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications (user_id);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS notifications;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS sensitivity;")
    sa.Enum(name="sensitivity").drop(op.get_bind(), checkfirst=True)

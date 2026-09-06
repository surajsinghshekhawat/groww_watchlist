"""Add note on watchlist items.

Revision ID: 0003_watchlist_notes
Revises: 0002_notifications_sensitivity
Create Date: 2026-09-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_watchlist_notes"
down_revision: Union[str, None] = "0002_notifications_sensitivity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='watchlist_items' AND column_name='note'
          ) THEN
            ALTER TABLE watchlist_items ADD COLUMN note TEXT;
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE watchlist_items DROP COLUMN IF EXISTS note;")

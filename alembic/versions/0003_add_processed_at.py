"""Add processed_at column for pipeline latency instrumentation.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-17
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE wiki_events ADD COLUMN IF NOT EXISTS processed_at TIMESTAMPTZ")


def downgrade() -> None:
    op.execute("ALTER TABLE wiki_events DROP COLUMN IF EXISTS processed_at")

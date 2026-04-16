"""Create metrics table.

Revision ID: 0001
Revises:
Create Date: 2026-04-16
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            ts          TIMESTAMPTZ         NOT NULL,
            hostname    TEXT                NOT NULL,
            category    TEXT                NOT NULL,
            metric      TEXT                NOT NULL,
            value       DOUBLE PRECISION    NOT NULL,
            unit        TEXT                NOT NULL,
            tags        TEXT,
            PRIMARY KEY (ts, hostname, category, metric)
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_metrics_host_cat_ts
            ON metrics (hostname, category, ts DESC)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_metrics_host_cat_ts")
    op.execute("DROP TABLE IF EXISTS metrics")

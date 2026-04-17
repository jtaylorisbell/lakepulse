"""Replace metrics table with wiki_events table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-17
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old hardware metrics table
    op.execute("DROP INDEX IF EXISTS idx_metrics_host_cat_ts")
    op.execute("DROP TABLE IF EXISTS metrics")

    # Create wiki events table
    op.execute("""
        CREATE TABLE IF NOT EXISTS wiki_events (
            event_id        BIGINT          NOT NULL,
            event_type      TEXT            NOT NULL,
            ts              TIMESTAMPTZ     NOT NULL,
            wiki            TEXT            NOT NULL,
            server_name     TEXT            NOT NULL,
            title           TEXT            NOT NULL,
            title_url       TEXT,
            user_name       TEXT            NOT NULL,
            is_bot          BOOLEAN         NOT NULL,
            is_minor        BOOLEAN         NOT NULL,
            is_new          BOOLEAN         NOT NULL,
            namespace       INTEGER         NOT NULL,
            comment         TEXT,
            length_old      INTEGER,
            length_new      INTEGER,
            revision_old    BIGINT,
            revision_new    BIGINT,
            meta_id         TEXT,
            meta_domain     TEXT            NOT NULL,
            ingested_at     TIMESTAMPTZ     NOT NULL,
            PRIMARY KEY (event_id)
        )
    """)

    # Indexes tuned for the 8 dashboard sections
    op.execute("CREATE INDEX idx_wiki_events_ts ON wiki_events (ts DESC)")
    op.execute("CREATE INDEX idx_wiki_events_bot_ts ON wiki_events (is_bot, ts DESC)")
    op.execute("CREATE INDEX idx_wiki_events_type_ts ON wiki_events (event_type, ts DESC)")
    op.execute("CREATE INDEX idx_wiki_events_wiki_ts ON wiki_events (wiki, ts DESC)")
    op.execute("CREATE INDEX idx_wiki_events_wiki_type_ts ON wiki_events (wiki, event_type, ts DESC)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_wiki_events_wiki_type_ts")
    op.execute("DROP INDEX IF EXISTS idx_wiki_events_wiki_ts")
    op.execute("DROP INDEX IF EXISTS idx_wiki_events_type_ts")
    op.execute("DROP INDEX IF EXISTS idx_wiki_events_bot_ts")
    op.execute("DROP INDEX IF EXISTS idx_wiki_events_ts")
    op.execute("DROP TABLE IF EXISTS wiki_events")

    # Recreate old metrics table
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
    op.execute("CREATE INDEX idx_metrics_host_cat_ts ON metrics (hostname, category, ts DESC)")

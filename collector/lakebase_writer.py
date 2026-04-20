"""Writes Wikipedia edit events directly to Lakebase (Postgres)."""

import logging
import time
from datetime import datetime, timezone
from urllib.parse import quote_plus

import psycopg

from config import LakebaseSettings

log = logging.getLogger("lakepulse.collector")

_UPSERT_SQL = """
    INSERT INTO wiki_events (
        event_id, event_type, ts, wiki, server_name, title, title_url,
        user_name, is_bot, is_minor, is_new, namespace, comment,
        length_old, length_new, revision_old, revision_new,
        meta_id, meta_domain, ingested_at, processed_at
    ) VALUES (
        %(event_id)s, %(event_type)s, %(ts)s, %(wiki)s, %(server_name)s,
        %(title)s, %(title_url)s, %(user_name)s, %(is_bot)s, %(is_minor)s,
        %(is_new)s, %(namespace)s, %(comment)s, %(length_old)s, %(length_new)s,
        %(revision_old)s, %(revision_new)s, %(meta_id)s, %(meta_domain)s,
        %(ingested_at)s, NOW()
    )
    ON CONFLICT (event_id) DO UPDATE SET
        event_type  = EXCLUDED.event_type,
        ts          = EXCLUDED.ts,
        wiki        = EXCLUDED.wiki,
        server_name = EXCLUDED.server_name,
        title       = EXCLUDED.title,
        title_url   = EXCLUDED.title_url,
        user_name   = EXCLUDED.user_name,
        is_bot      = EXCLUDED.is_bot,
        is_minor    = EXCLUDED.is_minor,
        is_new      = EXCLUDED.is_new,
        namespace   = EXCLUDED.namespace,
        comment     = EXCLUDED.comment,
        length_old  = EXCLUDED.length_old,
        length_new  = EXCLUDED.length_new,
        revision_old = EXCLUDED.revision_old,
        revision_new = EXCLUDED.revision_new,
        meta_id     = EXCLUDED.meta_id,
        meta_domain = EXCLUDED.meta_domain,
        ingested_at = EXCLUDED.ingested_at,
        processed_at = NOW()
"""


def _us_to_dt(us: int) -> datetime:
    """Convert microsecond UTC timestamp to a timezone-aware datetime."""
    return datetime.fromtimestamp(us / 1_000_000, tz=timezone.utc)


class LakebaseWriter:
    """Batch-upserts Wikipedia edit events into Lakebase via psycopg."""

    def __init__(self) -> None:
        self._settings = LakebaseSettings()
        self._conn: psycopg.Connection | None = None
        self._connect()

    def _build_dsn(self) -> str:
        host = self._settings.get_host()
        user = quote_plus(self._settings.get_user())
        password = quote_plus(self._settings.get_password())
        return f"postgresql://{user}:{password}@{host}:5432/{self._settings.database}?sslmode=require"

    def _connect(self) -> None:
        log.info("Connecting to Lakebase...")
        self._conn = psycopg.connect(self._build_dsn())
        self._conn.autocommit = False
        log.info("Connected to Lakebase")

    def _ensure_connection(self) -> None:
        if self._conn is None or self._conn.closed:
            self._connect()

    def write(self, records: list[dict]) -> int:
        """Upsert a batch of records. Returns the number of rows written."""
        params = []
        for r in records:
            row = dict(r)
            row["ts"] = _us_to_dt(row["ts"])
            row["ingested_at"] = _us_to_dt(row["ingested_at"])
            params.append(row)

        for attempt in range(3):
            try:
                self._ensure_connection()
                with self._conn.cursor() as cur:
                    cur.executemany(_UPSERT_SQL, params)
                self._conn.commit()
                return len(params)
            except (psycopg.OperationalError, psycopg.InterfaceError) as e:
                log.warning("Lakebase write failed (attempt %d/3): %s", attempt + 1, e)
                self._conn = None
                if attempt < 2:
                    time.sleep(2 ** attempt)

        log.error("Lakebase write failed after 3 attempts, dropping %d records", len(records))
        return 0

    def close(self) -> None:
        if self._conn and not self._conn.closed:
            self._conn.close()

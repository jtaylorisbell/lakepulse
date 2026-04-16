"""Lakebase (Postgres) connection pool for the web app."""

import os

import psycopg
from psycopg.rows import dict_row

LAKEBASE_DSN = os.environ.get(
    "LAKEBASE_DSN",
    "postgresql://user:pass@localhost:5432/lakepulse",
)


def get_connection() -> psycopg.Connection:
    return psycopg.connect(LAKEBASE_DSN, row_factory=dict_row)

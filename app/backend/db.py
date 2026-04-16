"""Lakebase (Postgres) connection for the web app."""

from urllib.parse import quote_plus

import psycopg
from psycopg.rows import dict_row

from config import LakebaseSettings

_lb = LakebaseSettings()


def _build_dsn() -> str:
    host = _lb.get_host()
    user = quote_plus(_lb.get_user())
    password = quote_plus(_lb.get_password())
    return f"postgresql://{user}:{password}@{host}:5432/{_lb.database}?sslmode=require"


def get_connection() -> psycopg.Connection:
    return psycopg.connect(_build_dsn(), row_factory=dict_row)

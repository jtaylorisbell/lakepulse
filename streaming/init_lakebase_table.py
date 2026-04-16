# Databricks notebook source
# MAGIC %md
# MAGIC # Initialize Lakebase metrics table
# MAGIC Creates the target table if it doesn't already exist.

# COMMAND ----------

import psycopg

LAKEBASE_PROJECT = "lakepulse"

from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
endpoint = w.api_client.do("GET", f"/api/2.0/lakebase/projects/{LAKEBASE_PROJECT}/branches/main/endpoints/default")
host = endpoint.get("host")
user = dbutils.secrets.get(scope="lakepulse", key="lakebase-user")
password = dbutils.secrets.get(scope="lakepulse", key="lakebase-pass")

# COMMAND ----------

dsn = f"postgresql://{user}:{password}@{host}:5432/lakepulse?sslmode=require"

with psycopg.connect(dsn) as conn:
    conn.execute("""
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
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_metrics_host_cat_ts
            ON metrics (hostname, category, ts DESC)
    """)
    conn.commit()

print("Lakebase metrics table ready")

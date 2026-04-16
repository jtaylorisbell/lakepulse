-- =============================================================================
-- LakePulse: Table setup for ZeroBus landing table and Lakebase serving table
-- Render with: envsubst < sql/setup.sql
-- =============================================================================

-- 1. ZeroBus Delta landing table (Unity Catalog)
--    ZeroBus writes directly into this table. Must exist before ingestion starts.
CREATE CATALOG IF NOT EXISTS ${LAKEPULSE_CATALOG};
CREATE SCHEMA IF NOT EXISTS ${LAKEPULSE_CATALOG}.${LAKEPULSE_SCHEMA};

CREATE TABLE IF NOT EXISTS ${LAKEPULSE_LANDING_TABLE} (
    ts          TIMESTAMP   NOT NULL,
    hostname    STRING      NOT NULL,
    category    STRING      NOT NULL,   -- cpu, memory, disk, network, battery, thermal, fan, gpu
    metric      STRING      NOT NULL,   -- e.g. cpu_percent, memory_used_bytes, disk_read_bytes
    value       DOUBLE      NOT NULL,
    unit        STRING      NOT NULL,   -- percent, bytes, celsius, rpm, bytes_per_sec, etc.
    tags        STRING                  -- JSON for extra context (core_id, interface, disk_name)
);

-- 2. Grant service principal access for ZeroBus ingestion
--    Replace <service-principal-id> with your actual SP application ID.
-- GRANT USE CATALOG ON CATALOG ${LAKEPULSE_CATALOG} TO `<service-principal-id>`;
-- GRANT USE SCHEMA ON SCHEMA ${LAKEPULSE_CATALOG}.${LAKEPULSE_SCHEMA} TO `<service-principal-id>`;
-- GRANT MODIFY, SELECT ON TABLE ${LAKEPULSE_LANDING_TABLE} TO `<service-principal-id>`;

-- 3. Lakebase serving table
--    Run this in your Lakebase Postgres instance.
--    The foreachwriter upserts into this table using (ts, hostname, category, metric) as PK.
CREATE TABLE IF NOT EXISTS metrics (
    ts          TIMESTAMPTZ     NOT NULL,
    hostname    TEXT            NOT NULL,
    category    TEXT            NOT NULL,
    metric      TEXT            NOT NULL,
    value       DOUBLE PRECISION NOT NULL,
    unit        TEXT            NOT NULL,
    tags        TEXT,
    PRIMARY KEY (ts, hostname, category, metric)
);

-- Index for the web app's typical queries (latest metrics by host, category)
CREATE INDEX IF NOT EXISTS idx_metrics_host_cat_ts
    ON metrics (hostname, category, ts DESC);

-- =============================================================================
-- LakePulse: Table setup for ZeroBus landing table and Lakebase serving table
-- Render with: source .env && envsubst < sql/setup.sql
-- =============================================================================

-- 1. ZeroBus Delta landing table (Unity Catalog)
--    ZeroBus writes directly into this table. Must exist before ingestion starts.
CREATE CATALOG IF NOT EXISTS ${LAKEPULSE_CATALOG};
CREATE SCHEMA IF NOT EXISTS ${LAKEPULSE_CATALOG}.${LAKEPULSE_SCHEMA};

CREATE TABLE IF NOT EXISTS ${LAKEPULSE_LANDING_TABLE} (
    event_id        BIGINT      NOT NULL,   -- Wikimedia event ID (globally unique)
    event_type      STRING      NOT NULL,   -- edit, new, log, categorize
    ts              TIMESTAMP   NOT NULL,   -- event timestamp
    wiki            STRING      NOT NULL,   -- e.g. enwiki, commonswiki
    server_name     STRING      NOT NULL,   -- e.g. en.wikipedia.org
    title           STRING      NOT NULL,   -- page title
    title_url       STRING,                 -- URL-encoded title path
    user_name       STRING      NOT NULL,   -- editor username or IP
    is_bot          BOOLEAN     NOT NULL,   -- bot edit flag
    is_minor        BOOLEAN     NOT NULL,   -- minor edit flag
    is_new          BOOLEAN     NOT NULL,   -- new page creation
    namespace       INT         NOT NULL,   -- MediaWiki namespace ID
    comment         STRING,                 -- edit summary
    length_old      INT,                    -- page length before edit (bytes)
    length_new      INT,                    -- page length after edit (bytes)
    revision_old    BIGINT,                 -- previous revision ID
    revision_new    BIGINT,                 -- new revision ID
    meta_id         STRING,                 -- event UUID
    meta_domain     STRING      NOT NULL,   -- meta.domain
    ingested_at     TIMESTAMP   NOT NULL    -- when collector received it
);

-- 2. Grant service principal access for ZeroBus ingestion
--    Replace <service-principal-id> with your actual SP application ID.
-- GRANT USE CATALOG ON CATALOG ${LAKEPULSE_CATALOG} TO `<service-principal-id>`;
-- GRANT USE SCHEMA ON SCHEMA ${LAKEPULSE_CATALOG}.${LAKEPULSE_SCHEMA} TO `<service-principal-id>`;
-- GRANT MODIFY, SELECT ON TABLE ${LAKEPULSE_LANDING_TABLE} TO `<service-principal-id>`;

-- 3. Lakebase serving table (reference only — managed by Alembic migrations)
--    See alembic/versions/ for the authoritative Postgres schema.

# LakePulse

Real-time Wikipedia edit monitoring, streamed through Databricks and displayed in a live dashboard.

```
Wikimedia SSE → Collector → ZeroBus → Delta Table → Spark Streaming → Lakebase → React Dashboard
```

LakePulse consumes the live stream of every edit across all Wikimedia wikis (~30-50 edits/sec), ingests them into a Delta table via ZeroBus, streams them into Lakebase with Spark Structured Streaming, and serves them through an 8-section analytics dashboard. The dashboard shows live event feeds, throughput metrics, pipeline latency breakdown, bot/human analysis, edit-type distributions, top wikis, biggest edits, searchable history, and pipeline health.

## Dashboard Sections

| Section | Description | Data Source |
|---------|-------------|-------------|
| Throughput Counters | Events/sec, writes/sec, total today | SQL aggregates (2s poll) |
| Pipeline Latency | Waterfall: ZeroBus→Delta vs Spark→Lakebase, p50/p95 | `ingested_at` / `processed_at` timestamps |
| Live Firehose | Scrolling feed of edits with wiki, user, type, bot/human, byte delta | SSE + REST polling (3s) |
| Bot vs Human | Donut chart + top bot/human editors | SQL GROUP BY (5s poll) |
| Edit Types | Donut: edit, new, log, categorize | SQL GROUP BY (5s poll) |
| Top Wikis | Horizontal bar chart of most active wikis | SQL GROUP BY (5s poll) |
| Biggest Edits | Ranked by absolute byte delta with size bars | SQL ORDER BY (5s poll) |
| Search & History | Full-text search by title/user/wiki with pagination and per-page edit timeline | On-demand SQL queries |
| Pipeline Health | SSE connection status, reconnect count, insert latency, event rate | Heartbeat rows + SQL aggregates (5s poll) |

## Project Structure

```
collector/                  # Python agent that consumes Wikimedia SSE and publishes to ZeroBus
  wiki_stream.py            #   SSE consumer with reconnection, canary filtering, event flattening
  zerobus_client.py         #   ZeroBus SDK wrapper (batched ack pattern)
  main.py                   #   Streaming loop entry point + heartbeat injection

streaming/                  # Databricks notebook
  stream_to_lakebase.py     #   Spark Structured Streaming: Delta → Lakebase (upsert on event_id)

app/                        # Databricks App
  backend/                  #   FastAPI backend (9 endpoints) querying Lakebase
    main.py                 #     API routes: SSE stream, REST events, stats, search, health
    models.py               #     Pydantic models
    db.py                   #     Lakebase connection (OAuth auto-resolved)
  frontend/                 #   React/Vite dashboard
    src/components/          #     13 components: Dashboard, Header, LiveFeed, EventRow, etc.
    src/hooks/               #     useEventStream (SSE + polling hybrid)
    src/api.ts               #     TypeScript API client + types

alembic/                    # Lakebase schema migrations
  versions/
    0001_create_metrics_table.py
    0002_wiki_events_table.py
    0003_add_processed_at.py

sql/setup.sql               # Delta landing table DDL (parameterized with envsubst)
config.py                   # Lakebase OAuth connection auto-resolver
databricks.yml              # DABs config: cluster, streaming job, app
```

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Node.js 18+
- Databricks workspace with:
  - Unity Catalog enabled
  - ZeroBus enabled
  - Lakebase provisioned (project name: `lakepulse`)
  - Databricks Apps enabled
- A service principal with OAuth credentials (client ID + secret) for ZeroBus ingestion
- Databricks CLI configured with a profile pointing to your workspace

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url> && cd lakepulse

# Python dependencies (includes ZeroBus SDK)
uv sync --extra collector

# Frontend dependencies
cd app/frontend && npm install && cd ../..
```

### 2. Configure environment

```bash
cp .env.example .env
```

#### (Optional) Create a service principal for ZeroBus

If you don't already have a service principal, create one and generate an OAuth secret:

```bash
# Create the service principal
DATABRICKS_CONFIG_PROFILE=your-profile \
  databricks service-principals create --display-name lakepulse-collector

# Note the application_id from the output, then generate a secret
DATABRICKS_CONFIG_PROFILE=your-profile \
  databricks service-principal-secrets create --service-principal-id <application-id>
```

The `create` command returns the `application_id` (use as `ZEROBUS_CLIENT_ID`). The `secrets create` command returns the `secret` (use as `ZEROBUS_CLIENT_SECRET`) — it is only shown once.

Edit `.env` with your values:

```bash
# Databricks CLI profile (used by backend, alembic, and DABs)
DATABRICKS_CONFIG_PROFILE=your-profile-name

# Databricks workspace URL
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com

# Service principal credentials for ZeroBus ingestion (collector only)
# Named ZEROBUS_* to avoid colliding with DATABRICKS_CLIENT_ID/SECRET
# which the Databricks SDK and CLI read automatically.
ZEROBUS_CLIENT_ID=your-service-principal-client-id
ZEROBUS_CLIENT_SECRET=your-service-principal-secret

# ZeroBus endpoint
ZEROBUS_ENDPOINT=your-workspace-id.zerobus.region.azuredatabricks.net

# Unity Catalog location for the Delta landing table
LAKEPULSE_CATALOG=your_catalog
LAKEPULSE_SCHEMA=default
# IMPORTANT: use the literal full table name (uv doesn't expand shell variables)
LAKEPULSE_LANDING_TABLE=your_catalog.default.wiki_events_raw
```

### 3. Create the Delta landing table

Render the DDL and run it in a Databricks SQL editor or via the CLI:

```bash
source .env && envsubst < sql/setup.sql
```

Then grant the service principal access:

```sql
GRANT MODIFY, SELECT ON TABLE your_catalog.default.wiki_events_raw
  TO `your-service-principal-client-id`;
```

### 4. Run Lakebase migrations

This creates the `wiki_events` table and indexes in your Lakebase Postgres instance:

```bash
DATABRICKS_CONFIG_PROFILE=your-profile uv run alembic upgrade head
```

You should see:

```
Running upgrade  -> 0001, Create metrics table.
Running upgrade 0001 -> 0002, Replace metrics table with wiki_events table.
Running upgrade 0002 -> 0003, Add processed_at column for pipeline latency instrumentation.
```

### 5. Deploy infrastructure

```bash
# Validate and deploy the streaming job and cluster via DABs
DATABRICKS_CONFIG_PROFILE=your-profile databricks bundle validate
DATABRICKS_CONFIG_PROFILE=your-profile databricks bundle deploy

# Deploy the Databricks App
DATABRICKS_CONFIG_PROFILE=your-profile databricks apps create lakepulse \
  --description "Real-time Wikipedia edits dashboard"
DATABRICKS_CONFIG_PROFILE=your-profile databricks apps deploy lakepulse \
  --source-code-path ./app

# Start the streaming job (runs indefinitely)
DATABRICKS_CONFIG_PROFILE=your-profile databricks bundle run stream_to_lakebase
```

The streaming job reads from the Delta landing table and writes to Lakebase using Spark Structured Streaming in real-time mode. It runs indefinitely until cancelled.

### 6. Start the collector

The collector consumes the Wikimedia EventStreams SSE endpoint and publishes events to ZeroBus:

```bash
# The collector needs the SP credentials for ZeroBus auth.
# If your shell has stale env vars, override LAKEPULSE_LANDING_TABLE explicitly.
LAKEPULSE_LANDING_TABLE=your_catalog.default.wiki_events_raw \
  uv run --env-file .env python -m collector.main
```

You should see:

```
INFO Starting LakePulse collector — Wikimedia EventStreams
INFO Connected to https://stream.wikimedia.org/v2/stream/recentchange
INFO Published 50 events (total: 50)
INFO Published 50 events (total: 100)
...
```

The collector auto-reconnects with `Last-Event-ID` when Wikimedia drops the connection (~every 15 minutes).

## Local Development

To run the dashboard locally (for development/debugging), start the FastAPI backend and Vite dev server in two terminals:

```bash
# Terminal 1: FastAPI backend
DATABRICKS_CONFIG_PROFILE=your-profile uv run uvicorn app.backend.main:app --reload --port 8000

# Terminal 2: Vite dev server (proxies /api to localhost:8000)
cd app/frontend && npm run dev
```

Open http://localhost:5173 — the dashboard will start showing live Wikipedia edits as they flow through the pipeline.

## Architecture

```
Wikimedia SSE ──→ Collector ──→ ZeroBus ──→ Delta Table ──→ Spark Streaming ──→ Lakebase ──→ Dashboard
  (public)       (Python)      (gRPC)     (Unity Catalog)  (real-time mode)   (Postgres)   (React+FastAPI)
```

| Component | Technology | Auth |
|-----------|-----------|------|
| Event source | Wikimedia EventStreams SSE | Public (User-Agent required) |
| Collector | Python + requests (SSE parsing) | N/A |
| Ingestion | ZeroBus gRPC (JSON mode) | OAuth M2M (service principal) |
| Landing table | Delta (Unity Catalog) | SP grants (MODIFY + SELECT) |
| Streaming | Spark Structured Streaming (real-time mode) | Workspace identity |
| Serving DB | Lakebase (Postgres-compatible) | OAuth (auto-resolved via Databricks SDK) |
| Backend | FastAPI + psycopg | OAuth (auto-resolved) |
| Frontend | React 19, Vite, Recharts, TanStack Query | N/A |
| Deployment | Databricks Apps + DABs | OAuth |
| Schema mgmt | Alembic | OAuth (auto-resolved) |

### Latency Instrumentation

The pipeline tracks three timestamps per event to measure latency at each stage:

| Timestamp | Set By | Meaning |
|-----------|--------|---------|
| `ts` | Wikimedia | When the edit was saved to the wiki database |
| `ingested_at` | Collector | When the collector received and published the event |
| `processed_at` | Spark | When Spark processed the event (added via `withColumn`) |

The dashboard computes pipeline latency as `NOW() - ingested_at` (ignoring Wikimedia internal delay), split into:
- **ZeroBus → Delta**: `processed_at - ingested_at`
- **Spark → Lakebase**: `NOW() - processed_at`

### Key Design Decisions

- **Flat schema**: ZeroBus and LakebaseForeachWriter reject nested types. All Wikimedia event fields are flattened at the collector level.
- **Single primary key**: `event_id` (Wikimedia's globally unique event ID) — simpler than the old 4-column composite PK.
- **Heartbeat injection**: The collector writes `_heartbeat` events every 5s with connection metadata. The backend filters these from user queries and reads them for pipeline health.
- **Hybrid live feed**: The frontend uses both SSE (for real-time push) and REST polling (3s fallback) to ensure the feed never goes stale.
- **Latency measurement**: Uses the most recent 100 events (not a time window) to avoid inflating latency with event age.

## Troubleshooting

**Collector gets 403 from Wikimedia**: The `User-Agent` header is required. This is set automatically in `wiki_stream.py`.

**ZeroBus rejects records with "unrecognized field name"**: The Delta landing table schema doesn't match the collector's JSON. Verify with `DESCRIBE your_catalog.default.wiki_events_raw`. If you recreated the table, the SP may need fresh `GRANT MODIFY, SELECT` permissions.

**Streaming job fails with "DIFFERENT_DELTA_TABLE_READ_BY_STREAMING_SOURCE"**: The checkpoint is bound to an old table ID. Delete it: `databricks fs rm --recursive dbfs:/tmp/lakepulse/checkpoints/stream_to_lakebase`

**Backend returns 500 "password authentication failed"**: Make sure `DATABRICKS_CONFIG_PROFILE` is set to your CLI profile. The SP credentials (`ZEROBUS_CLIENT_ID`/`ZEROBUS_CLIENT_SECRET`) won't interfere since they use a different name.

**Alembic fails with "password authentication failed"**: Same as above — set `DATABRICKS_CONFIG_PROFILE`: `DATABRICKS_CONFIG_PROFILE=your-profile uv run alembic upgrade head`

**Dashboard shows "Waiting for events"**: Check that (1) the collector is running and publishing, (2) the streaming job is running and not failed, (3) the backend can connect to Lakebase. Try `curl http://localhost:8000/api/events/recent?limit=1`.

**`uv run --env-file .env` uses wrong table name**: `uv` does not expand shell variables (`${VAR}`) in `.env` files. Use the literal full table name for `LAKEPULSE_LANDING_TABLE`.

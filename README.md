# LakePulse

Real-time Wikipedia edit monitoring, powered by Databricks and displayed in a live dashboard.

```
Wikimedia SSE  -->  Databricks App (FastAPI + collector thread)  -->  Lakebase  -->  React Dashboard
```

LakePulse consumes the live stream of every edit across all Wikimedia wikis (~30-50 edits/sec), writes them directly to Lakebase, and serves them through an analytics dashboard deployed as a Databricks App. The dashboard shows live event feeds, throughput metrics, write latency history, bot/human analysis, edit-type distributions, top wikis, biggest edits, searchable history, and pipeline health.

## Dashboard Sections

| Section | Description | Data Source |
|---------|-------------|-------------|
| Throughput Counters | Events/sec, total today | SQL aggregates (2s poll) |
| Write Latency | Line chart: Collector->Lakebase p50/p95 over 10 min | `/api/stats/latency-history` (2s poll) |
| Live Firehose | Scrolling feed of edits with wiki, user, type, bot/human, byte delta | SSE + REST polling (3s) |
| Bot vs Human | Donut chart + top bot/human editors | SQL GROUP BY (5s poll) |
| Edit Types | Donut: edit, new, log, categorize | SQL GROUP BY (5s poll) |
| Top Wikis | Horizontal bar chart of most active wikis | SQL GROUP BY (5s poll) |
| Biggest Edits | Ranked by absolute byte delta with size bars | SQL ORDER BY (5s poll) |
| Search & History | Full-text search by title/user/wiki with pagination and per-page edit timeline | On-demand SQL queries |
| Pipeline Health | SSE connection status, reconnect count, insert latency, event rate | Heartbeat rows + SQL aggregates (5s poll) |

## Project Structure

```
collector/                  # Wikipedia SSE collector (runs as background thread in the app)
  wiki_stream.py            #   SSE consumer with reconnection, canary filtering, event flattening
  lakebase_writer.py        #   Batch upsert to Lakebase via psycopg
  main.py                   #   Collector loop with heartbeat injection + stop signal support

app/                        # Databricks App
  backend/                  #   FastAPI backend (10 endpoints) querying Lakebase
    main.py                 #     API routes + lifespan (starts collector thread)
    models.py               #     Pydantic response models
    db.py                   #     Lakebase connection (OAuth auto-resolved)
  frontend/                 #   React/Vite dashboard
    src/components/         #     Dashboard, LiveFeed, LatencyChart, SearchPanel, etc.
    src/api.ts              #     TypeScript API client + types

alembic/                    # Lakebase schema migrations (run at deploy time)
  versions/
    0001_create_metrics_table.py
    0002_wiki_events_table.py
    0003_add_processed_at.py

config.py                   # LakebaseSettings: OAuth connection resolver via Databricks SDK
databricks.yml              # DABs bundle: Lakebase project + Databricks App
app.yaml                    # App startup command (migrations + uvicorn)
package.json                # Root workspace — delegates npm build to app/frontend
```

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Node.js 18+
- Databricks CLI (`brew install databricks/tap/databricks`)
- Databricks workspace with:
  - Lakebase enabled
  - Databricks Apps enabled
- Databricks CLI configured with a profile pointing to your workspace

## Deploy

```bash
git clone <repo-url> && cd lakepulse
cp .env.example .env
# Edit .env: set DATABRICKS_CONFIG_PROFILE and DATABRICKS_HOST

databricks bundle deploy
databricks apps deploy lakepulse \
  --source-code-path /Workspace/Users/<you>/.bundle/lakepulse/dev/files
```

That's it. `bundle deploy` creates the Lakebase project and Databricks App. `apps deploy` triggers the runtime which installs Python deps (via `uv`), builds the frontend (via `npm` workspace), runs Alembic migrations, and starts uvicorn with the embedded collector. The app's service principal owns the tables it creates, so no manual GRANTs are needed.

## Local Development

Local development connects to a **dev Lakebase branch** so you never touch the production database. The deployed app always uses the `production` branch.

### One-time setup

1. Install dependencies:

```bash
uv sync
cd app/frontend && npm install && cd ../..
```

2. Create a dev Lakebase branch:

```python
# uv run --env-file .env python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.postgres import Branch, BranchSpec

w = WorkspaceClient()
w.postgres.create_branch(
    parent="projects/lakepulse",
    branch_id="dev-your-name",
    branch=Branch(
        parent="projects/lakepulse/branches/production",
        spec=BranchSpec(no_expiry=True),
    ),
).wait()
```

3. Set `LAKEBASE_BRANCH_ID=dev-your-name` in your `.env`.

4. Run migrations on the dev branch:

```bash
uv run --env-file .env alembic upgrade head
```

### Running locally

```bash
# Terminal 1: FastAPI backend (starts collector thread automatically)
uv run --env-file .env uvicorn app.backend.main:app --reload --port 8000

# Terminal 2: Vite dev server (proxies /api to localhost:8000)
cd app/frontend && npm run dev
```

Open http://localhost:5173. The embedded collector will connect to Wikimedia SSE and start writing events to your dev Lakebase branch.

To run the collector standalone (without the web app):

```bash
uv run --env-file .env python -m collector.main
```

## Architecture

```
Wikimedia SSE ──> Databricks App ──> Lakebase ──> React Dashboard
  (public)        (FastAPI +          (Postgres)   (Vite + Recharts
                   collector thread)                + TanStack Query)
```

| Component | Technology | Auth |
|-----------|-----------|------|
| Event source | Wikimedia EventStreams SSE | Public (User-Agent required) |
| Collector | Python + requests (SSE parsing) | N/A (runs in-process) |
| Database | Lakebase (Postgres-compatible) | OAuth (auto-resolved via Databricks SDK) |
| Backend | FastAPI + psycopg | OAuth (auto-resolved) |
| Frontend | React 19, Vite, Recharts, TanStack Query | N/A |
| Deployment | Databricks Apps + DABs | OAuth |
| Schema mgmt | Alembic (runs at deploy time via `app.yaml`) | App SP identity |

### Latency Instrumentation

Each event carries two timestamps for measuring pipeline latency:

| Timestamp | Set By | Meaning |
|-----------|--------|---------|
| `ingested_at` | Collector | When the collector received the event from the SSE stream |
| `processed_at` | Lakebase writer | When the event was written to Lakebase (`NOW()` at INSERT time) |

The dashboard computes write latency as `processed_at - ingested_at` and displays p50/p95 over a 10-minute rolling window.

### Key Design Decisions

- **Direct writes**: The collector writes to Lakebase via psycopg upserts, skipping intermediate infrastructure (no message queue, no Delta table, no streaming job).
- **Embedded collector**: Runs as a background thread inside the FastAPI app. Simplifies deployment to two resources (Lakebase + App).
- **Time-based flush**: Events are batched up to 50 or flushed every 1 second, whichever comes first. Keeps write latency low while amortizing commit overhead.
- **Deploy-time migrations**: `app.yaml` runs `alembic upgrade head` before starting uvicorn. The app SP creates and owns the tables, so no manual GRANTs are needed.
- **Branch isolation**: Local development uses a Lakebase dev branch; the deployed app uses the production branch. Set via `LAKEBASE_BRANCH_ID` env var (defaults to `production`).
- **Dedicated schema**: All tables live in the `lakepulse` schema (created by `alembic/env.py`), not `public`. This avoids permission issues with Lakebase's restricted default schema.
- **Heartbeat injection**: The collector writes `_heartbeat` events every 5s with connection metadata. The backend filters these from user queries and reads them for pipeline health.
- **Flat schema**: All Wikimedia event fields are flattened at the collector level. No nested JSON in the database.

## Troubleshooting

**Collector gets 403 from Wikimedia**: The `User-Agent` header is required. This is set automatically in `wiki_stream.py`.

**Backend returns 500 "password authentication failed"**: Make sure `DATABRICKS_CONFIG_PROFILE` is set (for local dev) or the app has `CAN_CONNECT_AND_CREATE` on the Lakebase project (for deployed app). Check `databricks.yml` resources block.

**Alembic fails with "password authentication failed"**: Same as above. For local dev: `uv run --env-file .env alembic upgrade head`

**Alembic fails with "permission denied for schema public"**: Tables should be in the `lakepulse` schema, not `public`. Check that `alembic/env.py` includes `options=-csearch_path%3Dlakepulse` in the connection URL.

**Dashboard shows "Waiting for events"**: Check that the backend is running and the collector thread started (look for "Connecting to Wikimedia SSE stream" in logs). Try `curl http://localhost:8000/api/events/recent?limit=1`.

**Deployed app shows stale frontend**: The Databricks Apps runtime builds the frontend from source via the root `package.json` workspace. If you see old UI, redeploy: `databricks apps deploy lakepulse --source-code-path ...`

# LakePulse

Real-time Mac hardware metrics streamed through Databricks and displayed in a live dashboard.

```
Mac (psutil + powermetrics) → ZeroBus → Delta Table → Spark Streaming → Lakebase → Databricks App
```

LakePulse collects CPU, GPU, memory, disk, battery, thermal, fan, and network metrics from your Mac, ingests them into a Delta table via ZeroBus, streams them into Lakebase with Spark Structured Streaming, and serves them through a React dashboard deployed as a Databricks App.

## Project Structure

```
collector/                  # Python agent that collects Mac metrics and publishes to ZeroBus
  metrics.py                #   psutil + powermetrics collection
  zerobus_client.py         #   ZeroBus SDK wrapper
  main.py                   #   Collection loop entry point

streaming/                  # Databricks notebooks
  init_lakebase_table.py    #   Creates the Lakebase target table
  stream_to_lakebase.py     #   Spark Structured Streaming: Delta → Lakebase (upsert)

app/                        # Databricks App
  backend/                  #   FastAPI backend querying Lakebase
  frontend/                 #   React/Vite dashboard with Recharts
  requirements.txt          #   App runtime dependencies

sql/setup.sql               # Parameterized DDL for Delta landing table + grants
databricks.yml              # DABs config: Lakebase, streaming job, and app
```

## Prerequisites

- Python 3.12+, [uv](https://docs.astral.sh/uv/), Node.js 18+
- Databricks workspace with Unity Catalog, ZeroBus, Lakebase, and Apps enabled
- A service principal with OAuth credentials for ZeroBus ingestion

## Setup

### 1. Install dependencies

```bash
uv sync --extra collector    # Python deps + ZeroBus SDK
cd app/frontend && npm install && cd ../..
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in your workspace, service principal, and Lakebase details
```

The table name is configured once via `LAKEPULSE_CATALOG`, `LAKEPULSE_SCHEMA`, and `LAKEPULSE_LANDING_TABLE` in `.env`. All components read from these variables.

### 3. Create the Delta landing table

```bash
source .env && envsubst < sql/setup.sql
# Run the rendered SQL in a Databricks SQL editor
```

### 4. Deploy infrastructure with DABs

The streaming job, Lakebase instance, and web app are all managed by Databricks Asset Bundles:

```bash
databricks bundle validate
databricks bundle deploy
databricks bundle run stream_to_lakebase
```

### 5. Run the collector

```bash
export $(grep -v '^#' .env | grep -v '<' | xargs)

# With thermal/fan/GPU data (requires sudo for powermetrics)
sudo -E uv run python -m collector.main

# Without sudo (skips powermetrics gracefully)
uv run python -m collector.main
```

### 6. Build and deploy the app

```bash
cd app/frontend && npm run build && cd ../..
databricks bundle deploy
```

## Local Development

Run the FastAPI backend and Vite dev server separately for hot reload:

```bash
# Backend (proxied by Vite in dev)
uv run uvicorn app.backend.main:app --reload

# Frontend (in a separate terminal)
cd app/frontend && npm run dev
```

The Vite dev server proxies `/api` requests to `localhost:8000`.

## Architecture Details

| Component | Technology | Auth |
|---|---|---|
| Metrics collection | psutil, powermetrics (macOS) | Local |
| Ingestion | ZeroBus gRPC (JSON mode) | OAuth M2M (service principal) |
| Landing table | Delta (Unity Catalog) | SP grants |
| Streaming | Spark Structured Streaming (real-time mode) | Workspace identity |
| Serving DB | Lakebase (Postgres-compatible) | Username/password |
| Backend | FastAPI, psycopg | Lakebase DSN |
| Frontend | React, Vite, Recharts, TanStack Query | N/A |
| Deployment | Databricks Apps + DABs | OAuth |

The streaming job uses [lakebase-foreachwriter](https://github.com/christophergrant/lakebase-foreachwriter) in upsert mode with `(ts, hostname, category, metric)` as the primary key.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LakePulse is a real-time Mac hardware metrics monitoring application. It collects system metrics from macOS (CPU, GPU, memory, disk, battery, thermals, fan speed, network), streams them through Databricks infrastructure, and displays them in a live React dashboard deployed as a Databricks App.

## Architecture

```
Mac (psutil + powermetrics) → ZeroBus gRPC → Delta Table → Spark Real-Time Streaming → Lakebase → Databricks App (React/Vite + FastAPI)
```

### Pipeline Stages

1. **Metrics Collector** (`collector/`) — Python agent running locally on macOS. Uses `psutil` for CPU/memory/disk/network/battery and `powermetrics` (subprocess, requires sudo) for thermals/fan/GPU. Publishes JSON records to ZeroBus via `databricks-zerobus-ingest-sdk`.

2. **ZeroBus Ingestion** — Serverless push-based gRPC ingestion. Writes directly into a Unity Catalog Delta landing table. The target table must be pre-created with a matching schema. Uses OAuth via service principal (client ID + secret). SDK package: `databricks-zerobus-ingest-sdk`.

3. **Spark Real-Time Streaming** — Databricks notebook/job using Structured Streaming in real-time mode. Reads from the ZeroBus Delta landing table and writes to Lakebase using `lakebase-foreachwriter` (upsert mode on metric primary keys). Reference: [christophergrant/lakebase-foreachwriter](https://github.com/christophergrant/lakebase-foreachwriter).

4. **Lakebase** — Postgres-compatible database. Serves as the low-latency query layer for the web app. The foreachwriter connects via `psycopg` with username/password auth (Lakebase does not yet support OAuth for direct connections).

5. **Web App** (`app/`) — Databricks App with a React/Vite frontend and FastAPI backend. Backend queries Lakebase (Postgres) and exposes REST endpoints. Frontend polls or uses SSE for live metric updates.

### Configuration

Table names and catalog/schema are configured once in `.env` via `LAKEPULSE_CATALOG`, `LAKEPULSE_SCHEMA`, and `LAKEPULSE_LANDING_TABLE`. All other components read from these:

- `sql/setup.sql` — uses `${LAKEPULSE_*}` placeholders; render with `source .env && envsubst < sql/setup.sql`
- `collector/` — reads `LAKEPULSE_LANDING_TABLE` from env
- `streaming/` — builds the table name from spark conf, defaults to `lakepulse.default.metrics_raw`

Infrastructure (Lakebase, streaming job, app) is provisioned via DABs (`databricks.yml`).

### Key Constraints

- All Databricks service integrations use **OAuth authentication** (never Personal Access Tokens)
- Python package management uses **uv** (never pip). Use `uv add <package>` to add dependencies.
- Lakebase schema is managed by Alembic migrations (`alembic/`), following the pattern from [jtaylorisbell/lakebase-ops](https://github.com/jtaylorisbell/lakebase-ops). Connection is auto-resolved via Databricks SDK OAuth in `config.py`.
- ZeroBus requires a pre-created Delta table and service principal with MODIFY + SELECT grants
- The `powermetrics` macOS command requires sudo for thermal/fan/GPU data

## Commands

```bash
# Install dependencies
uv sync

# Add a dependency
uv add <package>

# Run metrics collector locally
sudo uv run --env-file .env python -m collector.main

# Run web app locally
uv run uvicorn app.backend.main:app --reload

# Frontend dev server
cd app/frontend && npm run dev

# Run Lakebase migrations
uv run alembic upgrade head

# Create a new migration
uv run alembic revision -m "description"
```

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LakePulse is a real-time Wikipedia edit monitoring application. It ingests live edit events from Wikimedia EventStreams (SSE), streams them through Databricks infrastructure, and displays them in a live React dashboard deployed as a Databricks App. The dashboard shows live event feeds, throughput metrics, bot/human analysis, edit-type breakdowns, top wikis, biggest edits, searchable history, and pipeline health.

## Architecture

```
Wikimedia SSE → Collector (Python) → ZeroBus gRPC → Delta Table → Spark Real-Time Streaming → Lakebase → Databricks App (React/Vite + FastAPI)
```

### Pipeline Stages

1. **Event Collector** (`collector/`) — Python agent that consumes the Wikimedia EventStreams SSE endpoint (`https://stream.wikimedia.org/v2/stream/recentchange`). Flattens nested event JSON, filters canary events, handles auto-reconnection with `Last-Event-ID`, and publishes batches to ZeroBus via `databricks-zerobus-ingest-sdk`.

2. **ZeroBus Ingestion** — Serverless push-based gRPC ingestion. Writes directly into a Unity Catalog Delta landing table (`wiki_events_raw`). The target table must be pre-created with a matching flat schema. Uses OAuth via service principal (client ID + secret). SDK package: `databricks-zerobus-ingest-sdk`.

3. **Spark Real-Time Streaming** — Databricks notebook/job using Structured Streaming in real-time mode. Reads from the ZeroBus Delta landing table and writes to Lakebase using `lakebase-foreachwriter` (upsert mode on `event_id` primary key).

4. **Lakebase** — Postgres-compatible database. Serves as the low-latency query layer for the web app. Table `wiki_events` stores flattened Wikipedia edit events with indexes tuned for the 8 dashboard sections.

5. **Web App** (`app/`) — Databricks App with a React/Vite frontend and FastAPI backend. Backend exposes 9 REST endpoints (live SSE stream, recent events, throughput stats, bot/human split, edit types, top wikis, biggest edits, search, pipeline health). Frontend uses SSE for live feed and TanStack Query for polling analytics.

### Configuration

Table names and catalog/schema are configured once in `.env` via `LAKEPULSE_CATALOG`, `LAKEPULSE_SCHEMA`, and `LAKEPULSE_LANDING_TABLE`. All other components read from these:

- `sql/setup.sql` — uses `${LAKEPULSE_*}` placeholders; render with `source .env && envsubst < sql/setup.sql`
- `collector/` — reads `LAKEPULSE_LANDING_TABLE` from env
- `streaming/` — builds the table name from DABs parameters

Infrastructure (Lakebase, streaming job, app) is provisioned via DABs (`databricks.yml`).

### Key Constraints

- All Databricks service integrations use **OAuth authentication** (never Personal Access Tokens)
- Python package management uses **uv** (never pip). Use `uv add <package>` to add dependencies.
- Lakebase schema is managed by Alembic migrations (`alembic/`), following the pattern from [jtaylorisbell/lakebase-ops](https://github.com/jtaylorisbell/lakebase-ops). Connection is auto-resolved via Databricks SDK OAuth in `config.py`.
- ZeroBus requires a pre-created Delta table and service principal with MODIFY + SELECT grants
- Wikimedia SSE drops connections every ~15 minutes; the collector auto-reconnects with `Last-Event-ID`
- The collector injects `_heartbeat` events for pipeline health monitoring

## Commands

```bash
# Install dependencies
uv sync

# Add a dependency
uv add <package>

# Run Wikipedia event collector locally
uv run --env-file .env python -m collector.main

# Run web app locally
uv run uvicorn app.backend.main:app --reload

# Frontend dev server
cd app/frontend && npm run dev

# Build frontend for production
cd app/frontend && npm run build

# Run Lakebase migrations
uv run alembic upgrade head

# Create a new migration
uv run alembic revision -m "description"
```

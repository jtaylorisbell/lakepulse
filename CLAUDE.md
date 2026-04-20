# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LakePulse is a real-time Wikipedia edit monitoring application. It ingests live edit events from Wikimedia EventStreams (SSE), writes them directly to Lakebase, and displays them in a live React dashboard deployed as a Databricks App. The dashboard shows live event feeds, throughput metrics, bot/human analysis, edit-type breakdowns, top wikis, biggest edits, searchable history, and pipeline health.

## Architecture

```
Wikimedia SSE → Databricks App (FastAPI + collector thread) → Lakebase → React frontend
```

### Components

1. **Event Collector** (`collector/`) — Runs as a background thread inside the FastAPI app. Consumes the Wikimedia EventStreams SSE endpoint (`https://stream.wikimedia.org/v2/stream/recentchange`), flattens nested event JSON, filters canary events, handles auto-reconnection with `Last-Event-ID`, and batch-upserts directly into Lakebase via `psycopg`.

2. **Lakebase** — Postgres-compatible database. Serves as the low-latency query layer for the web app. Table `wiki_events` stores flattened Wikipedia edit events with indexes tuned for the 8 dashboard sections.

3. **Web App** (`app/`) — Databricks App with a React/Vite frontend and FastAPI backend. The backend starts the collector thread on startup and exposes 9 REST endpoints (live SSE stream, recent events, throughput stats, bot/human split, edit types, top wikis, biggest edits, search, pipeline health). Frontend uses SSE for live feed and TanStack Query for polling analytics.

### Configuration

Lakebase connection is auto-resolved via Databricks SDK OAuth in `config.py` using `LakebaseSettings`.

Infrastructure (Lakebase, app) is provisioned via DABs (`databricks.yml`).

### Key Constraints

- All Databricks service integrations use **OAuth authentication** (never Personal Access Tokens)
- Python package management uses **uv** (never pip). Use `uv add <package>` to add dependencies.
- Lakebase schema is managed by Alembic migrations (`alembic/`), following the pattern from [jtaylorisbell/lakebase-ops](https://github.com/jtaylorisbell/lakebase-ops). Connection is auto-resolved via Databricks SDK OAuth in `config.py`.
- Wikimedia SSE drops connections every ~15 minutes; the collector auto-reconnects with `Last-Event-ID`
- The collector injects `_heartbeat` events for pipeline health monitoring

## Commands

```bash
# Install dependencies
uv sync

# Add a dependency
uv add <package>

# Run web app locally (starts collector thread automatically)
uv run uvicorn app.backend.main:app --reload

# Run collector standalone (without the web app)
uv run --env-file .env python -m collector.main

# Frontend dev server
cd app/frontend && npm run dev

# Build frontend for production
cd app/frontend && npm run build

# Run Lakebase migrations
uv run alembic upgrade head

# Create a new migration
uv run alembic revision -m "description"
```

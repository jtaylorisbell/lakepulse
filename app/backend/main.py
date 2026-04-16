"""FastAPI backend for LakePulse — serves metrics from Lakebase."""

import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.backend.db import get_connection
from app.backend.models import MetricRecord, MetricSummary

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="LakePulse", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/metrics/latest")
def get_latest_metrics(hostname: str | None = None) -> list[MetricSummary]:
    """Get the most recent value for each metric."""
    query = """
        SELECT DISTINCT ON (category, metric, tags)
            category, metric, value, unit, tags, ts
        FROM metrics
        {where}
        ORDER BY category, metric, tags, ts DESC
    """
    where = "WHERE hostname = %(hostname)s" if hostname else ""
    with get_connection() as conn:
        rows = conn.execute(query.format(where=where), {"hostname": hostname}).fetchall()
    return [MetricSummary(**row) for row in rows]


@app.get("/api/metrics/history")
def get_metric_history(
    category: str,
    metric: str,
    minutes: int = Query(default=30, le=1440),
    hostname: str | None = None,
) -> list[MetricRecord]:
    """Get time series for a specific metric over the last N minutes."""
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    query = """
        SELECT ts, hostname, category, metric, value, unit, tags
        FROM metrics
        WHERE category = %(category)s
          AND metric = %(metric)s
          AND ts >= %(since)s
          {host_filter}
        ORDER BY ts ASC
    """
    host_filter = "AND hostname = %(hostname)s" if hostname else ""
    params = {"category": category, "metric": metric, "since": since, "hostname": hostname}
    with get_connection() as conn:
        rows = conn.execute(query.format(host_filter=host_filter), params).fetchall()
    return [MetricRecord(**row) for row in rows]


@app.get("/api/metrics/categories")
def get_categories() -> list[str]:
    """List all metric categories."""
    with get_connection() as conn:
        rows = conn.execute("SELECT DISTINCT category FROM metrics ORDER BY category").fetchall()
    return [row["category"] for row in rows]


# Serve frontend static files in production
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{path:path}")
    def serve_frontend(path: str):
        file = FRONTEND_DIR / path
        if file.exists() and file.is_file():
            return FileResponse(file)
        return FileResponse(FRONTEND_DIR / "index.html")

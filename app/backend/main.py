"""FastAPI backend for LakePulse — serves live Wikipedia edit data from Lakebase."""

import asyncio
import logging
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.backend.db import get_connection
from app.backend.models import (
    BiggestEdit,
    BotHumanSplit,
    EditTypeBreakdown,
    LatencyStage,
    PipelineHealth,
    SearchResult,
    ThroughputStats,
    WikiActivity,
    WikiEvent,
)
from collector.main import run as collector_run

log = logging.getLogger("lakepulse.app")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"

# Filter clause used in all user-facing queries to exclude heartbeat rows
_NO_HEARTBEAT = "event_type != '_heartbeat'"


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = threading.Event()
    collector_thread = threading.Thread(
        target=collector_run,
        args=(stop_event,),
        daemon=True,
        name="lakepulse-collector",
    )
    collector_thread.start()
    log.info("Collector thread started")
    yield
    stop_event.set()
    collector_thread.join(timeout=10)
    log.info("Collector thread stopped")


app = FastAPI(title="LakePulse", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _row_to_event(row: dict) -> WikiEvent:
    """Convert a database row to a WikiEvent, computing size_delta."""
    size_delta = None
    if row.get("length_new") is not None and row.get("length_old") is not None:
        size_delta = row["length_new"] - row["length_old"]
    return WikiEvent(**row, size_delta=size_delta)


# ── Section 1: Live Firehose ─────────────────────────────────────────────────


@app.get("/api/events/stream")
async def stream_events():
    """SSE endpoint that pushes new wiki events as they arrive in Lakebase."""
    async def event_generator():
        # Seed from the latest event so we stream forward from now, not from the beginning
        with get_connection() as conn:
            seed = conn.execute(
                f"SELECT MAX(event_id) AS max_id FROM wiki_events WHERE {_NO_HEARTBEAT}"
            ).fetchone()
        last_event_id = (seed["max_id"] or 0) if seed else 0

        while True:
            with get_connection() as conn:
                rows = conn.execute(
                    f"""SELECT * FROM wiki_events
                        WHERE {_NO_HEARTBEAT} AND event_id > %(last_id)s
                        ORDER BY ts ASC LIMIT 50""",
                    {"last_id": last_event_id},
                ).fetchall()

            for row in rows:
                event = _row_to_event(row)
                last_event_id = event.event_id
                yield f"id: {event.event_id}\ndata: {event.model_dump_json()}\n\n"

            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/events/recent")
def get_recent_events(limit: int = Query(default=50, le=200)) -> list[WikiEvent]:
    """Get the most recent wiki events."""
    with get_connection() as conn:
        rows = conn.execute(
            f"""SELECT * FROM wiki_events
                WHERE {_NO_HEARTBEAT}
                ORDER BY ts DESC LIMIT %(limit)s""",
            {"limit": limit},
        ).fetchall()
    return [_row_to_event(row) for row in rows]


# ── Section 2: Throughput Counters ───────────────────────────────────────────


@app.get("/api/stats/throughput")
def get_throughput(window_seconds: int = Query(default=60, le=300)) -> ThroughputStats:
    """Throughput and latency stats over a recent time window."""
    with get_connection() as conn:
        # Throughput from the full window
        tp_row = conn.execute(
            f"""SELECT COUNT(*)::float / %(window)s AS events_per_sec
                FROM wiki_events
                WHERE {_NO_HEARTBEAT}
                  AND ts > NOW() - MAKE_INTERVAL(secs := %(window)s)""",
            {"window": window_seconds},
        ).fetchone()

        # Latency from the most recent 100 events — avoids window-age bias
        # Stage 1: ingested_at → processed_at (collector SSE receipt → Lakebase write)
        # Stage 2: processed_at → NOW() (Lakebase write → dashboard query)
        lat_row = conn.execute(
            f"""SELECT
                    COALESCE(percentile_cont(0.5) WITHIN GROUP (
                        ORDER BY EXTRACT(EPOCH FROM (NOW() - ingested_at)) * 1000
                    ), 0) AS latency_p50_ms,
                    COALESCE(percentile_cont(0.95) WITHIN GROUP (
                        ORDER BY EXTRACT(EPOCH FROM (NOW() - ingested_at)) * 1000
                    ), 0) AS latency_p95_ms,
                    COALESCE(percentile_cont(0.5) WITHIN GROUP (
                        ORDER BY EXTRACT(EPOCH FROM (COALESCE(processed_at, ingested_at) - ingested_at)) * 1000
                    ), 0) AS write_p50,
                    COALESCE(percentile_cont(0.95) WITHIN GROUP (
                        ORDER BY EXTRACT(EPOCH FROM (COALESCE(processed_at, ingested_at) - ingested_at)) * 1000
                    ), 0) AS write_p95,
                    COALESCE(percentile_cont(0.5) WITHIN GROUP (
                        ORDER BY EXTRACT(EPOCH FROM (NOW() - COALESCE(processed_at, ingested_at))) * 1000
                    ), 0) AS query_p50,
                    COALESCE(percentile_cont(0.95) WITHIN GROUP (
                        ORDER BY EXTRACT(EPOCH FROM (NOW() - COALESCE(processed_at, ingested_at))) * 1000
                    ), 0) AS query_p95
                FROM (
                    SELECT ingested_at, processed_at FROM wiki_events
                    WHERE {_NO_HEARTBEAT}
                    ORDER BY ts DESC LIMIT 100
                ) recent""",
        ).fetchone()

        today_row = conn.execute(
            f"""SELECT COUNT(*) AS cnt FROM wiki_events
                WHERE {_NO_HEARTBEAT} AND ts >= CURRENT_DATE""",
        ).fetchone()

    eps = tp_row["events_per_sec"] or 0
    return ThroughputStats(
        events_per_sec=eps,
        writes_per_sec=eps,
        latency_p50_ms=round(lat_row["latency_p50_ms"] or 0, 1),
        latency_p95_ms=round(lat_row["latency_p95_ms"] or 0, 1),
        total_events_today=today_row["cnt"],
        stages=[
            LatencyStage(
                label="Collector \u2192 Lakebase",
                p50_ms=round(lat_row["write_p50"] or 0, 1),
                p95_ms=round(lat_row["write_p95"] or 0, 1),
            ),
            LatencyStage(
                label="Lakebase \u2192 Dashboard",
                p50_ms=round(lat_row["query_p50"] or 0, 1),
                p95_ms=round(lat_row["query_p95"] or 0, 1),
            ),
        ],
    )


# ── Section 2b: Latency History ────────────────────────────────────────────


@app.get("/api/stats/latency-history")
def get_latency_history(
    minutes: int = Query(default=10, le=60),
    bucket_seconds: int = Query(default=2, le=30),
) -> list[dict]:
    """Historical write latency (p50/p95) in time buckets."""
    with get_connection() as conn:
        rows = conn.execute(
            f"""SELECT
                    time_bucket AS ts,
                    COALESCE(percentile_cont(0.5) WITHIN GROUP (
                        ORDER BY EXTRACT(EPOCH FROM (processed_at - ingested_at)) * 1000
                    ), 0) AS p50,
                    COALESCE(percentile_cont(0.95) WITHIN GROUP (
                        ORDER BY EXTRACT(EPOCH FROM (processed_at - ingested_at)) * 1000
                    ), 0) AS p95
                FROM (
                    SELECT
                        ingested_at, processed_at,
                        date_trunc('second', processed_at)
                            - (EXTRACT(SECOND FROM processed_at)::int %% %(bucket)s) * INTERVAL '1 second'
                            AS time_bucket
                    FROM wiki_events
                    WHERE {_NO_HEARTBEAT}
                      AND processed_at IS NOT NULL
                      AND processed_at > NOW() - MAKE_INTERVAL(secs := %(window)s)
                ) bucketed
                GROUP BY time_bucket
                ORDER BY time_bucket""",
            {"window": minutes * 60, "bucket": bucket_seconds},
        ).fetchall()

    return [
        {"ts": row["ts"].isoformat(), "p50": round(row["p50"], 1), "p95": round(row["p95"], 1)}
        for row in rows
    ]


# ── Section 3: Bot vs Human ─────────────────────────────────────────────────


@app.get("/api/stats/bot-human")
def get_bot_human(minutes: int = Query(default=5, le=60)) -> BotHumanSplit:
    """Bot vs human activity split with top editors."""
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    with get_connection() as conn:
        counts = conn.execute(
            f"""SELECT is_bot, COUNT(*) AS cnt FROM wiki_events
                WHERE {_NO_HEARTBEAT} AND ts > %(since)s
                GROUP BY is_bot""",
            {"since": since},
        ).fetchall()

        top_bots = conn.execute(
            f"""SELECT user_name, COUNT(*) AS count FROM wiki_events
                WHERE {_NO_HEARTBEAT} AND is_bot AND ts > %(since)s
                GROUP BY user_name ORDER BY count DESC LIMIT 10""",
            {"since": since},
        ).fetchall()

        top_humans = conn.execute(
            f"""SELECT user_name, COUNT(*) AS count FROM wiki_events
                WHERE {_NO_HEARTBEAT} AND NOT is_bot AND ts > %(since)s
                GROUP BY user_name ORDER BY count DESC LIMIT 10""",
            {"since": since},
        ).fetchall()

    bot_count = 0
    human_count = 0
    for row in counts:
        if row["is_bot"]:
            bot_count = row["cnt"]
        else:
            human_count = row["cnt"]

    total = bot_count + human_count
    return BotHumanSplit(
        total=total,
        bot_count=bot_count,
        human_count=human_count,
        bot_percent=round(bot_count / total * 100, 1) if total else 0,
        top_bots=[dict(r) for r in top_bots],
        top_humans=[dict(r) for r in top_humans],
    )


# ── Section 4: Edit Type Breakdown ──────────────────────────────────────────


@app.get("/api/stats/edit-types")
def get_edit_types(minutes: int = Query(default=5, le=60)) -> EditTypeBreakdown:
    """Breakdown of event types in the recent window."""
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    with get_connection() as conn:
        rows = conn.execute(
            f"""SELECT event_type, COUNT(*) AS cnt FROM wiki_events
                WHERE {_NO_HEARTBEAT} AND ts > %(since)s
                GROUP BY event_type""",
            {"since": since},
        ).fetchall()

    breakdown = {}
    for row in rows:
        breakdown[row["event_type"]] = row["cnt"]

    return EditTypeBreakdown(
        edit=breakdown.get("edit", 0),
        new=breakdown.get("new", 0),
        log=breakdown.get("log", 0),
        categorize=breakdown.get("categorize", 0),
    )


# ── Section 5: Top Active Wikis ──────────────────────────────────────────────


@app.get("/api/stats/top-wikis")
def get_top_wikis(
    minutes: int = Query(default=5, le=60),
    limit: int = Query(default=15, le=50),
) -> list[WikiActivity]:
    """Top wikis by event volume in the recent window."""
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    window_sec = minutes * 60
    with get_connection() as conn:
        rows = conn.execute(
            f"""SELECT wiki, server_name, COUNT(*) AS count
                FROM wiki_events
                WHERE {_NO_HEARTBEAT} AND ts > %(since)s
                GROUP BY wiki, server_name
                ORDER BY count DESC LIMIT %(limit)s""",
            {"since": since, "limit": limit},
        ).fetchall()

    return [
        WikiActivity(
            wiki=r["wiki"],
            server_name=r["server_name"],
            count=r["count"],
            events_per_sec=round(r["count"] / window_sec, 2),
        )
        for r in rows
    ]


# ── Section 6: Biggest Edits ────────────────────────────────────────────────


@app.get("/api/stats/biggest-edits")
def get_biggest_edits(
    minutes: int = Query(default=5, le=60),
    limit: int = Query(default=20, le=100),
) -> list[BiggestEdit]:
    """Biggest edits by absolute byte delta in the recent window."""
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    with get_connection() as conn:
        rows = conn.execute(
            f"""SELECT event_id, title, title_url, wiki, user_name,
                       (length_new - length_old) AS size_delta, ts
                FROM wiki_events
                WHERE {_NO_HEARTBEAT}
                  AND length_old IS NOT NULL AND length_new IS NOT NULL
                  AND ts > %(since)s
                ORDER BY ABS(length_new - length_old) DESC
                LIMIT %(limit)s""",
            {"since": since, "limit": limit},
        ).fetchall()

    return [BiggestEdit(**r) for r in rows]


# ── Section 7: Search ────────────────────────────────────────────────────────


@app.get("/api/events/search")
def search_events(
    q: str | None = None,
    wiki: str | None = None,
    user: str | None = None,
    event_type: str | None = None,
    minutes: int = Query(default=60, le=1440),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, le=200),
) -> SearchResult:
    """Search and filter wiki events with pagination."""
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    conditions = [_NO_HEARTBEAT, "ts > %(since)s"]
    params: dict = {"since": since}

    if q:
        conditions.append("title ILIKE %(q)s")
        params["q"] = f"%{q}%"
    if wiki:
        conditions.append("wiki = %(wiki)s")
        params["wiki"] = wiki
    if user:
        conditions.append("user_name ILIKE %(user)s")
        params["user"] = f"%{user}%"
    if event_type:
        conditions.append("event_type = %(event_type)s")
        params["event_type"] = event_type

    where = " AND ".join(conditions)
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    with get_connection() as conn:
        count_row = conn.execute(
            f"SELECT COUNT(*) AS cnt FROM wiki_events WHERE {where}", params
        ).fetchone()

        rows = conn.execute(
            f"""SELECT * FROM wiki_events
                WHERE {where}
                ORDER BY ts DESC
                LIMIT %(limit)s OFFSET %(offset)s""",
            params,
        ).fetchall()

    return SearchResult(
        events=[_row_to_event(row) for row in rows],
        total_count=count_row["cnt"],
    )


# ── Section 8: Pipeline Health ───────────────────────────────────────────────


@app.get("/api/health/pipeline")
def get_pipeline_health() -> PipelineHealth:
    """Pipeline health metrics derived from event data and heartbeats."""
    with get_connection() as conn:
        last_event = conn.execute(
            f"SELECT MAX(ts) AS ts FROM wiki_events WHERE {_NO_HEARTBEAT}"
        ).fetchone()

        heartbeat = conn.execute(
            """SELECT ts, comment FROM wiki_events
               WHERE event_type = '_heartbeat'
               ORDER BY ts DESC LIMIT 1"""
        ).fetchone()

        latency = conn.execute(
            f"""SELECT AVG(EXTRACT(EPOCH FROM (NOW() - ingested_at)) * 1000) AS avg_ms
                FROM (
                    SELECT ingested_at FROM wiki_events
                    WHERE {_NO_HEARTBEAT}
                    ORDER BY ts DESC LIMIT 50
                ) recent"""
        ).fetchone()

        minute_count = conn.execute(
            f"""SELECT COUNT(*) AS cnt FROM wiki_events
                WHERE {_NO_HEARTBEAT}
                  AND ts > NOW() - INTERVAL '1 minute'"""
        ).fetchone()

    # Parse heartbeat comment for reconnect count
    reconnect_count = 0
    sse_connected = False
    if heartbeat:
        comment = heartbeat.get("comment", "") or ""
        if "connected=True" in comment:
            # Consider connected if heartbeat is recent (< 30s)
            hb_ts = heartbeat["ts"]
            if hb_ts and (datetime.now(timezone.utc) - hb_ts).total_seconds() < 30:
                sse_connected = True
        for part in comment.split():
            if part.startswith("reconnects="):
                try:
                    reconnect_count = int(part.split("=")[1])
                except ValueError:
                    pass

    return PipelineHealth(
        sse_connected=sse_connected,
        last_event_ts=last_event["ts"] if last_event else None,
        last_heartbeat_ts=heartbeat["ts"] if heartbeat else None,
        reconnect_count=reconnect_count,
        insert_latency_avg_ms=round(latency["avg_ms"] or 0, 1) if latency else 0,
        events_in_last_minute=minute_count["cnt"] if minute_count else 0,
    )


# ── Static Files ─────────────────────────────────────────────────────────────

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{path:path}")
    def serve_frontend(path: str):
        file = FRONTEND_DIR / path
        if file.exists() and file.is_file():
            return FileResponse(file)
        return FileResponse(FRONTEND_DIR / "index.html")

"""Pydantic models for the LakePulse Wikipedia edits API."""

from datetime import datetime

from pydantic import BaseModel


class WikiEvent(BaseModel):
    event_id: int
    event_type: str
    ts: datetime
    wiki: str
    server_name: str
    title: str
    title_url: str | None = None
    user_name: str
    is_bot: bool
    is_minor: bool
    is_new: bool
    namespace: int
    comment: str | None = None
    length_old: int | None = None
    length_new: int | None = None
    revision_old: int | None = None
    revision_new: int | None = None
    size_delta: int | None = None


class LatencyStage(BaseModel):
    label: str
    p50_ms: float
    p95_ms: float


class ThroughputStats(BaseModel):
    events_per_sec: float
    writes_per_sec: float
    latency_p50_ms: float
    latency_p95_ms: float
    total_events_today: int
    stages: list[LatencyStage] = []


class BotHumanSplit(BaseModel):
    total: int
    bot_count: int
    human_count: int
    bot_percent: float
    top_bots: list[dict]
    top_humans: list[dict]


class EditTypeBreakdown(BaseModel):
    edit: int = 0
    new: int = 0
    log: int = 0
    categorize: int = 0


class WikiActivity(BaseModel):
    wiki: str
    server_name: str
    count: int
    events_per_sec: float


class BiggestEdit(BaseModel):
    event_id: int
    title: str
    wiki: str
    user_name: str
    size_delta: int
    ts: datetime


class PipelineHealth(BaseModel):
    sse_connected: bool
    last_event_ts: datetime | None = None
    last_heartbeat_ts: datetime | None = None
    reconnect_count: int = 0
    insert_latency_avg_ms: float = 0.0
    events_in_last_minute: int = 0


class SearchResult(BaseModel):
    events: list[WikiEvent]
    total_count: int

"""Pydantic models for the LakePulse API."""

from datetime import datetime

from pydantic import BaseModel


class MetricRecord(BaseModel):
    ts: datetime
    hostname: str
    category: str
    metric: str
    value: float
    unit: str
    tags: str | None = None


class MetricSummary(BaseModel):
    category: str
    metric: str
    latest_value: float
    unit: str
    tags: str | None = None
    ts: datetime

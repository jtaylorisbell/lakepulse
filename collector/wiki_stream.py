"""Consume Wikimedia EventStreams SSE and yield flattened edit events."""

import json
import logging
import os
import time
from collections.abc import Iterator
from datetime import datetime, timezone

import requests

log = logging.getLogger("lakepulse.collector")

STREAM_URL = os.environ.get(
    "WIKIMEDIA_STREAM_URL",
    "https://stream.wikimedia.org/v2/stream/recentchange",
)

# Reconnection state — exposed so main.py can read it for heartbeats
reconnect_count: int = 0
last_event_id: str | None = None
connected: bool = False


def connect(resume_from: str | None = None) -> requests.Response:
    """Open an SSE connection to Wikimedia EventStreams.

    If *resume_from* is provided it is sent as the ``Last-Event-ID`` header
    so the server replays events from that point.
    """
    headers = {
        "Accept": "text/event-stream",
        "User-Agent": "LakePulse/0.1 (https://github.com/jtaylorisbell/lakepulse; taylor.isbell@databricks.com)",
    }
    if resume_from:
        headers["Last-Event-ID"] = resume_from
    resp = requests.get(STREAM_URL, stream=True, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp


def parse_sse_events(response: requests.Response) -> Iterator[tuple[str | None, dict]]:
    """Yield ``(event_id, parsed_data)`` from an SSE byte stream.

    Implements the SSE line protocol: accumulates ``data:`` lines, captures
    the ``id:`` field, and emits a complete event on each blank line.
    """
    event_id: str | None = None
    data_lines: list[str] = []

    for raw_line in response.iter_lines(decode_unicode=True):
        if raw_line is None:
            continue
        line = raw_line if isinstance(raw_line, str) else raw_line.decode("utf-8")

        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
        elif line.startswith("id:"):
            event_id = line[3:].lstrip()
        elif line == "":
            # Blank line signals end of an event
            if data_lines:
                payload = "\n".join(data_lines)
                try:
                    yield event_id, json.loads(payload)
                except json.JSONDecodeError:
                    log.warning("Skipping malformed JSON event")
                data_lines = []
        # Ignore other fields (event:, retry:, comments starting with :)


def flatten_event(event: dict) -> dict | None:
    """Flatten a Wikimedia recentchange event into the Delta table schema.

    Returns ``None`` for canary events or events missing required fields.
    """
    meta = event.get("meta", {})
    if meta.get("domain") == "canary":
        return None

    # Required fields — skip malformed events
    event_id = event.get("id")
    if event_id is None:
        return None

    length = event.get("length") or {}
    revision = event.get("revision") or {}

    return {
        "event_id": event_id,
        "event_type": event.get("type", ""),
        "ts": int(event.get("timestamp", time.time()) * 1_000_000),
        "wiki": event.get("wiki", ""),
        "server_name": event.get("server_name", ""),
        "title": event.get("title", ""),
        "title_url": event.get("title_url", ""),
        "user_name": event.get("user", ""),
        "is_bot": event.get("bot", False),
        "is_minor": event.get("minor", False),
        "is_new": event.get("type") == "new",
        "namespace": event.get("namespace", 0),
        "comment": event.get("comment", ""),
        "length_old": length.get("old"),
        "length_new": length.get("new"),
        "revision_old": revision.get("old"),
        "revision_new": revision.get("new"),
        "meta_id": meta.get("id", ""),
        "meta_domain": meta.get("domain", ""),
        "ingested_at": int(datetime.now(timezone.utc).timestamp() * 1_000_000),
    }


def stream_events(batch_size: int = 50) -> Iterator[list[dict]]:
    """Yield batches of flattened events from the Wikimedia SSE stream.

    Handles auto-reconnection with ``Last-Event-ID`` when the connection
    drops (Wikimedia enforces a ~15-minute timeout).
    """
    global reconnect_count, last_event_id, connected

    while True:
        try:
            log.info("Connecting to Wikimedia SSE stream%s",
                     f" (resuming from {last_event_id})" if last_event_id else "")
            resp = connect(resume_from=last_event_id)
            connected = True
            log.info("Connected to %s", STREAM_URL)

            batch: list[dict] = []
            for eid, raw_event in parse_sse_events(resp):
                if eid:
                    last_event_id = eid

                record = flatten_event(raw_event)
                if record is None:
                    continue

                batch.append(record)
                if len(batch) >= batch_size:
                    yield batch
                    batch = []

        except (requests.ConnectionError, requests.Timeout,
                requests.exceptions.ChunkedEncodingError) as exc:
            connected = False
            reconnect_count += 1
            log.warning("SSE connection lost (%s), reconnecting in 1s (attempt #%d)",
                        type(exc).__name__, reconnect_count)
            time.sleep(1)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            connected = False
            reconnect_count += 1
            log.error("Unexpected error in SSE stream: %s, reconnecting in 2s", exc)
            time.sleep(2)

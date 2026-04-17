"""LakePulse collector: streams live Wikipedia edits and publishes to ZeroBus."""

import logging
import time
from datetime import datetime, timezone

from collector import wiki_stream
from collector.zerobus_client import ZeroBusPublisher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("lakepulse.collector")

HEARTBEAT_INTERVAL = 5  # seconds
BATCH_SIZE = 50


def _make_heartbeat() -> dict:
    """Create a heartbeat record with collector connection state."""
    now_us = int(datetime.now(timezone.utc).timestamp() * 1_000_000)
    return {
        "event_id": -1,
        "event_type": "_heartbeat",
        "ts": now_us,
        "wiki": "",
        "server_name": "",
        "title": "",
        "title_url": "",
        "user_name": "lakepulse-collector",
        "is_bot": False,
        "is_minor": False,
        "is_new": False,
        "namespace": 0,
        "comment": f"connected={wiki_stream.connected} reconnects={wiki_stream.reconnect_count} last_eid={wiki_stream.last_event_id}",
        "length_old": None,
        "length_new": None,
        "revision_old": None,
        "revision_new": None,
        "meta_id": "",
        "meta_domain": "heartbeat",
        "ingested_at": now_us,
    }


def main() -> None:
    log.info("Starting LakePulse collector — Wikimedia EventStreams")
    publisher = ZeroBusPublisher()
    last_heartbeat = time.monotonic()
    total_published = 0

    try:
        for batch in wiki_stream.stream_events(batch_size=BATCH_SIZE):
            # Inject heartbeat if enough time has passed
            now = time.monotonic()
            if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                batch.append(_make_heartbeat())
                last_heartbeat = now

            publisher.publish(batch)
            total_published += len(batch)
            log.info("Published %d events (total: %d)", len(batch), total_published)

    except KeyboardInterrupt:
        log.info("Shutting down (published %d events total)", total_published)
    finally:
        publisher.close()


if __name__ == "__main__":
    main()

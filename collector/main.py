"""LakePulse collector: streams live Wikipedia edits and writes to Lakebase."""

import logging
import threading
import time
from datetime import datetime, timezone

from collector import wiki_stream
from collector.lakebase_writer import LakebaseWriter

log = logging.getLogger("lakepulse.collector")

HEARTBEAT_INTERVAL = 5  # seconds
BATCH_SIZE = 50
FLUSH_INTERVAL = 1.0  # seconds — flush partial batches to keep latency low


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


def run(stop_event: threading.Event | None = None) -> None:
    """Main collector loop. Set stop_event to signal shutdown from another thread."""
    log.info("Starting LakePulse collector — Wikimedia EventStreams → Lakebase")
    writer = LakebaseWriter()
    last_heartbeat = time.monotonic()
    total_written = 0

    try:
        for batch in wiki_stream.stream_events(batch_size=BATCH_SIZE, flush_interval=FLUSH_INTERVAL):
            if stop_event and stop_event.is_set():
                log.info("Stop signal received, shutting down collector")
                break

            now = time.monotonic()
            if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                batch.append(_make_heartbeat())
                last_heartbeat = now

            written = writer.write(batch)
            total_written += written
            log.info("Wrote %d events to Lakebase (total: %d)", written, total_written)

    except KeyboardInterrupt:
        log.info("Shutting down (wrote %d events total)", total_written)
    finally:
        writer.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()


if __name__ == "__main__":
    main()

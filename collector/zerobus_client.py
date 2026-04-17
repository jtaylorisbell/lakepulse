"""ZeroBus SDK client for publishing wiki events to Delta table."""

import logging
import os
import threading

from zerobus.sdk.sync import ZerobusSdk
from zerobus.sdk.shared import (
    AckCallback,
    RecordType,
    StreamConfigurationOptions,
    TableProperties,
)

log = logging.getLogger("lakepulse.collector")


class _AckTracker(AckCallback):
    """Tracks in-flight records and logs errors."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.in_flight = 0
        self.acked = 0
        self.errors = 0

    def on_ack(self, offset: int) -> None:
        with self._lock:
            self.in_flight -= 1
            self.acked += 1

    def on_error(self, offset: int, error_message: str) -> None:
        with self._lock:
            self.in_flight -= 1
            self.errors += 1
        log.error("ZeroBus ack error at offset %d: %s", offset, error_message)

    def record_sent(self) -> None:
        with self._lock:
            self.in_flight += 1


class ZeroBusPublisher:
    """Publishes event records to a Databricks Delta table via ZeroBus."""

    def __init__(
        self,
        server_endpoint: str | None = None,
        workspace_url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        table: str | None = None,
    ):
        self.server_endpoint = server_endpoint or os.environ["ZEROBUS_ENDPOINT"]
        self.workspace_url = workspace_url or os.environ["DATABRICKS_HOST"]
        self.client_id = client_id or os.environ["ZEROBUS_CLIENT_ID"]
        self.client_secret = client_secret or os.environ["ZEROBUS_CLIENT_SECRET"]
        self.table = table or os.environ.get("LAKEPULSE_LANDING_TABLE", "lakepulse.default.wiki_events_raw")
        log.info("ZeroBus target table: %s", self.table)
        log.info("ZeroBus endpoint: %s", self.server_endpoint)

        self._ack_tracker = _AckTracker()
        self._sdk = ZerobusSdk(self.server_endpoint, self.workspace_url)
        table_props = TableProperties(self.table)
        options = StreamConfigurationOptions(
            record_type=RecordType.JSON,
            ack_callback=self._ack_tracker,
        )
        self._stream = self._sdk.create_stream(
            self.client_id, self.client_secret, table_props, options,
        )

    def publish(self, records: list[dict]) -> None:
        """Send a batch of records to ZeroBus with async ack tracking."""
        for record in records:
            self._ack_tracker.record_sent()
            self._stream.ingest_record_offset(record)

    @property
    def stats(self) -> dict:
        return {
            "in_flight": self._ack_tracker.in_flight,
            "acked": self._ack_tracker.acked,
            "errors": self._ack_tracker.errors,
        }

    def close(self) -> None:
        self._stream.close()

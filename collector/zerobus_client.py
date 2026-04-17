"""ZeroBus SDK client for publishing wiki events to Delta table."""

import logging
import os

from zerobus.sdk.sync import ZerobusSdk

log = logging.getLogger("lakepulse.collector")
from zerobus.sdk.shared import RecordType, StreamConfigurationOptions, TableProperties


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

        self._sdk = ZerobusSdk(self.server_endpoint, self.workspace_url)
        table_props = TableProperties(self.table)
        options = StreamConfigurationOptions(record_type=RecordType.JSON)
        self._stream = self._sdk.create_stream(
            self.client_id, self.client_secret, table_props, options,
        )

    def publish(self, records: list[dict]) -> None:
        """Send a batch of records to ZeroBus with batched ack waiting."""
        acks = []
        for record in records:
            acks.append(self._stream.ingest_record(record))
        for ack in acks:
            ack.wait_for_ack()

    def close(self) -> None:
        self._stream.close()

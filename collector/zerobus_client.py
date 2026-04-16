"""ZeroBus SDK client for publishing metrics to Delta table."""

import os

from zerobus.sdk.sync import ZerobusSdk
from zerobus.sdk.shared import RecordType, StreamConfigurationOptions, TableProperties


class ZeroBusPublisher:
    """Publishes metric records to a Databricks Delta table via ZeroBus."""

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
        self.client_id = client_id or os.environ["DATABRICKS_CLIENT_ID"]
        self.client_secret = client_secret or os.environ["DATABRICKS_CLIENT_SECRET"]
        self.table = table or os.environ.get("LAKEPULSE_LANDING_TABLE", "lakepulse.default.metrics_raw")

        self._sdk = ZerobusSdk(self.server_endpoint, self.workspace_url)
        table_props = TableProperties(self.table)
        options = StreamConfigurationOptions(record_type=RecordType.JSON)
        self._stream = self._sdk.create_stream(
            self.client_id, self.client_secret, table_props, options,
        )

    def publish(self, records: list[dict]) -> None:
        """Send a batch of metric records to ZeroBus."""
        for record in records:
            ack = self._stream.ingest_record(record)
            ack.wait_for_ack()

    def close(self) -> None:
        self._stream.close()

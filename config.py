"""Lakebase connection settings with Databricks SDK auto-resolution.

Follows the pattern from github.com/jtaylorisbell/lakebase-ops.
"""

import logging
import os
import time

from databricks.sdk import WorkspaceClient
from pydantic_settings import BaseSettings

log = logging.getLogger(__name__)


class _OAuthTokenManager:
    """Caches OAuth tokens with automatic refresh."""

    def __init__(self, workspace_client: WorkspaceClient, endpoint: str):
        self._w = workspace_client
        self._endpoint = endpoint
        self._token: str | None = None
        self._expires_at: float = 0

    def get_token(self) -> str:
        if self._token and time.time() < self._expires_at:
            return self._token
        log.info("Generating new Lakebase OAuth token")
        cred = self._w.postgres.generate_database_credential(endpoint=self._endpoint)
        self._token = cred.token
        # Refresh 5 minutes before the 60-minute expiry
        self._expires_at = time.time() + 55 * 60
        return self._token


class LakebaseSettings(BaseSettings):
    """Auto-resolves Lakebase connection parameters from Databricks identity."""

    model_config = {"env_prefix": "LAKEBASE_"}

    project_id: str = "lakepulse"
    branch_id: str = ""
    endpoint_id: str = "primary"
    database: str = "databricks_postgres"

    def _get_workspace_client(self) -> WorkspaceClient:
        return WorkspaceClient()

    def get_branch_id(self) -> str:
        if self.branch_id:
            return self.branch_id
        if os.environ.get("LAKEBASE_BRANCH_ID"):
            return os.environ["LAKEBASE_BRANCH_ID"]
        return "production"

    def get_host(self) -> str:
        w = self._get_workspace_client()
        branch = self.get_branch_id()
        name = f"projects/{self.project_id}/branches/{branch}/endpoints/{self.endpoint_id}"
        endpoint = w.postgres.get_endpoint(name)
        return endpoint.status.hosts.host

    def get_user(self) -> str:
        w = self._get_workspace_client()
        me = w.current_user.me()
        if me.user_name:
            return me.user_name
        # Service principal
        return me.application_id

    def get_password(self) -> str:
        w = self._get_workspace_client()
        branch = self.get_branch_id()
        endpoint = f"projects/{self.project_id}/branches/{branch}/endpoints/{self.endpoint_id}"
        mgr = _OAuthTokenManager(w, endpoint)
        return mgr.get_token()

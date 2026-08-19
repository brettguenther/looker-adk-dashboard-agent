"""Configuration settings for Looker Dashboard Agent."""

from __future__ import annotations

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Looker Instance & OAuth
    lookersdk_base_url: str = os.getenv("LOOKERSDK_BASE_URL", "")
    auth_id: str = os.getenv("AUTH_ID", "looker-oauth")
    looker_oauth_client_id: Optional[str] = os.getenv("LOOKER_OAUTH_CLIENT_ID", None)
    looker_oauth_client_secret: Optional[str] = os.getenv("LOOKER_OAUTH_CLIENT_SECRET", None)
    lookersdk_verify_ssl: bool = True

    # GCP / Vertex AI settings
    google_cloud_project: Optional[str] = os.getenv("GOOGLE_CLOUD_PROJECT", None)
    google_cloud_location: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    vertexai_location: str = os.getenv("VERTEXAI_LOCATION", "global")
    agent_id: str = os.getenv("AGENT_ID", "looker-dashboard-agent")
    agent_display_name: str = os.getenv("AGENT_DISPLAY_NAME", "Looker Dashboard Architect")
    llm_model: str = os.getenv("LLM_MODEL", "gemini-3.6-flash")

    # Local development token override fallback
    local_dev_token: Optional[str] = os.getenv("LOOKER_DEV_TOKEN", os.getenv("LOOKERSDK_ACCESS_TOKEN", None))

    @property
    def mcp_url(self) -> str:
        """Construct the Looker Managed MCP server URL."""
        base = self.lookersdk_base_url.rstrip("/")
        return f"{base}/mcp"

    @property
    def api_base_url(self) -> str:
        """Construct the Looker API 4.0 URL."""
        base = self.lookersdk_base_url.rstrip("/")
        return f"{base}/api/4.0"


settings = Settings()

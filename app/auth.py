"""Authentication and state context resolution utilities for Looker OAuth in Gemini Enterprise."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)


def _extract_key_from_context(ctx: Any, key: str) -> Any:
    """Safely extracts a key from state or session state of an ADK context."""
    if ctx is None:
        return None

    # 1. Check direct state dictionary (ToolContext, InvocationContext, CallbackContext)
    state = getattr(ctx, "state", None)
    if isinstance(state, dict) and key in state:
        return state.get(key)

    # 2. Check session.state dictionary
    session = getattr(ctx, "session", None)
    if session and hasattr(session, "state") and isinstance(session.state, dict):
        if key in session.state:
            return session.state.get(key)

    return None


def get_looker_cli_profile(
    profile_name: Optional[str] = None,
    auto_refresh: bool = True,
) -> Optional[Dict[str, Any]]:
    """Reads and parses active Looker profile from ~/.config/looker-cli/config.yaml.

    If auto_refresh is enabled and looker-cli is installed, automatically calls
    'looker-cli user me' to refresh an expired token if needed.
    """
    config_dir = os.environ.get("LOOKER_CLI_CONFIG_DIR")
    config_path = (
        Path(config_dir) / "config.yaml"
        if config_dir
        else Path.home() / ".config" / "looker-cli" / "config.yaml"
    )

    if not config_path.exists():
        return None

    try:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
            if not isinstance(cfg, dict):
                return None

        profiles = cfg.get("profiles", {})
        target_name = profile_name or cfg.get("default") or cfg.get("active_profile")
        if not target_name and profiles:
            target_name = next(iter(profiles))

        if not target_name or target_name not in profiles:
            return None

        pdata = profiles[target_name]
        host = pdata.get("host", "localhost")
        port_val = pdata.get("port", 443)
        try:
            port = int(port_val)
        except (ValueError, TypeError):
            port = 443

        ssl = pdata.get("ssl", True)
        protocol = "https" if ssl else "http"
        base_url = f"{protocol}://{host}" if (ssl and port == 443) or (not ssl and port == 80) else f"{protocol}://{host}:{port}"

        access_token = pdata.get("access_token")

        # Auto-refresh if access token missing or expired
        if auto_refresh and not access_token:
            try:
                subprocess.run(
                    ["looker-cli", "user", "me", "--profile", target_name],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=15,
                )
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                    pdata = cfg.get("profiles", {}).get(target_name, {})
                    access_token = pdata.get("access_token")
            except Exception as e:
                logger.debug("Auto-refresh via looker-cli failed: %s", e)

        return {
            "name": target_name,
            "host": host,
            "port": port,
            "ssl": ssl,
            "base_url": base_url,
            "access_token": access_token,
            "refresh_token": pdata.get("refresh_token"),
            "expiration": pdata.get("expiration"),
        }
    except Exception as e:
        logger.debug("Failed reading looker-cli config: %s", e)
        return None


def resolve_auth_token(ctx: Optional[Any] = None) -> Optional[str]:
    """Resolves the Looker Bearer authorization token dynamically.

    Resolution precedence:
    1. Looker OAuth token injected into ADK context state under AUTH_ID by Gemini Enterprise
    2. LOOKER_DEV_TOKEN / LOOKERSDK_ACCESS_TOKEN from environment
    3. Active session token from ~/.config/looker-cli/config.yaml (if present)
    """
    auth_key = settings.auth_id

    # 1. Check ADK Context
    if ctx is not None:
        token = _extract_key_from_context(ctx, auth_key)
        if token:
            logger.debug("Looker Bearer token resolved from ADK context state (%s).", auth_key)
            return str(token)

    # 2. Check environment variable override
    dev_token = settings.local_dev_token or os.environ.get("LOOKER_DEV_TOKEN") or os.environ.get("LOOKERSDK_ACCESS_TOKEN")
    if dev_token:
        logger.debug("Using development token override from environment.")
        return str(dev_token)

    # 3. Check local looker-cli config fallback
    cli_profile = get_looker_cli_profile(auto_refresh=True)
    if cli_profile and cli_profile.get("access_token"):
        logger.debug("Using active session token from looker-cli profile '%s'.", cli_profile.get("name"))
        return cli_profile["access_token"]

    logger.warning("Looker authentication token could not be resolved from ADK context, environment, or CLI config.")
    return None


def resolve_looker_base_url() -> str:
    """Resolves the Looker base URL from settings, environment, or looker-cli profile."""
    if settings.lookersdk_base_url:
        return settings.lookersdk_base_url.rstrip("/")

    env_url = os.environ.get("LOOKERSDK_BASE_URL") or os.environ.get("LOOKER_BASE_URL")
    if env_url:
        return env_url.rstrip("/")

    cli_profile = get_looker_cli_profile(auto_refresh=False)
    if cli_profile and cli_profile.get("base_url"):
        return cli_profile["base_url"].rstrip("/")

    return ""


def get_auth_headers(ctx: Optional[Any] = None) -> Dict[str, str]:
    """Constructs HTTP headers with the resolved Looker Bearer token."""
    token = resolve_auth_token(ctx)
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-Looker-Token"] = f"token {token}"
    return headers

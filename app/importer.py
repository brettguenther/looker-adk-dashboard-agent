"""Looker Dashboard Importer using LookML import API and preferred_slug in-place updates."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional
import requests
import yaml

from app.auth import get_auth_headers
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ImportedDashboardResult:
    id: str
    title: str
    slug: str
    folder_id: Optional[str]
    folder_name: Optional[str]
    url: str
    api_url: str
    raw_response: Dict[str, Any]


def sanitize_lookml_yaml(lookml_yaml: str, preferred_slug: Optional[str] = None) -> str:
    """Sanitize LookML YAML, removing invalid top-level slug fields and ensuring valid preferred_slug."""
    try:
        data = yaml.safe_load(lookml_yaml)
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            # Remove invalid top-level 'slug' which causes API 422
            data[0].pop("slug", None)
            if preferred_slug and re.match(r"^[A-Za-z0-9_-]{10,50}$", preferred_slug):
                data[0]["preferred_slug"] = str(preferred_slug)
            elif "preferred_slug" in data[0] and not re.match(r"^[A-Za-z0-9_-]{10,50}$", str(data[0]["preferred_slug"])):
                data[0].pop("preferred_slug", None)
            return yaml.dump(data, sort_keys=False)
    except Exception:
        pass

    # Regex cleanup fallback
    lookml_yaml = re.sub(r"\n\s+slug:\s*[^\n]+", "", lookml_yaml)
    if preferred_slug and re.match(r"^[A-Za-z0-9_-]{10,50}$", preferred_slug) and "preferred_slug:" not in lookml_yaml:
        lookml_yaml = re.sub(
            r"(-\s*dashboard:\s*[^\n]+)",
            rf'\1\n  preferred_slug: "{preferred_slug}"',
            lookml_yaml,
            count=1,
        )
    return lookml_yaml


def inject_preferred_slug(lookml_yaml: str, preferred_slug: Optional[str]) -> str:
    return sanitize_lookml_yaml(lookml_yaml, preferred_slug)


class LookerDashboardImporter:
    """Imports LookML dashboard YAML into Looker as an interactive User-Defined Dashboard (UDD)."""

    def __init__(self, api_base_url: Optional[str] = None):
        self.api_base_url = (api_base_url or settings.api_base_url).rstrip("/")
        self.instance_base_url = settings.lookersdk_base_url.rstrip("/")

    def import_lookml(
        self,
        lookml_yaml: str,
        folder_id: Optional[str] = None,
        preferred_slug: Optional[str] = None,
        ctx: Optional[Any] = None,
    ) -> ImportedDashboardResult:
        """Import LookML dashboard string into Looker.

        If preferred_slug is provided, Looker overwrites the existing dashboard in-place.
        """
        if preferred_slug:
            lookml_yaml = inject_preferred_slug(lookml_yaml, preferred_slug)

        payload: Dict[str, Any] = {"lookml": lookml_yaml}
        if folder_id:
            payload["folder_id"] = str(folder_id)

        url = f"{self.api_base_url}/dashboards/lookml"
        headers = get_auth_headers(ctx)

        logger.info("Importing LookML dashboard to %s", url)
        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=45,
            verify=settings.lookersdk_verify_ssl,
        )

        if resp.status_code >= 400:
            logger.error("Dashboard import failed (%d): %s", resp.status_code, resp.text)
            resp.raise_for_status()

        data = resp.json()
        dash_id = str(data.get("id"))
        slug = data.get("slug") or dash_id
        folder_info = data.get("folder", {})
        folder_id_res = str(data.get("folder_id") or folder_info.get("id") or "")
        folder_name = folder_info.get("name")

        return ImportedDashboardResult(
            id=dash_id,
            title=data.get("title", "Untitled Dashboard"),
            slug=slug,
            folder_id=folder_id_res,
            folder_name=folder_name,
            url=f"{self.instance_base_url}/dashboards/{slug}",
            api_url=f"{self.api_base_url}/dashboards/{dash_id}",
            raw_response=data,
        )


dashboard_importer = LookerDashboardImporter()

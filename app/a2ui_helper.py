"""A2UI (Agent-to-User Interface) v0.9 Payload and Response Builder for Looker Dashboards in Gemini Enterprise."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def build_dashboard_a2ui_payload(
    dashboard_id: str,
    slug: str,
    title: str,
    embed_url: str,
    looker_url: str,
    folder_name: Optional[str] = None,
    tile_count: int = 0,
    verified_count: int = 0,
    model_name: Optional[str] = None,
    explore_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Constructs official A2UI v0.9 message envelope for Gemini Enterprise / Agentspace.

    Conforms to https://a2ui.org/specification/v0_9/material_catalog.json specification
    using `IFrameSrcdoc` for rich sandboxed embed rendering.
    """
    surface_id = f"looker-dashboard-{slug}"
    catalog_id = "https://a2ui.org/specification/v0_9/material_catalog.json"

    status_text = f"{verified_count}/{tile_count} Verified" if tile_count > 0 else "Live Looker"
    
    # Sandboxed HTML payload for IFrameSrcdoc
    html_content = (
        "<!DOCTYPE html>"
        "<html>"
        "<head>"
        "<meta charset='utf-8'>"
        "<style>"
        "body { margin: 0; padding: 0; overflow: hidden; background: #fafafa; font-family: 'Google Sans', Roboto, sans-serif; }"
        "iframe { border: none; width: 100%; height: 750px; display: block; border-radius: 8px; }"
        "</style>"
        "</head>"
        "<body>"
        f"<iframe src=\"{embed_url}\" width=\"100%\" height=\"750\" allowfullscreen loading=\"lazy\"></iframe>"
        "</body>"
        "</html>"
    )

    components: List[Dict[str, Any]] = [
        {
            "id": "root",
            "component": "MaterialCard",
            "appearance": "outlined",
            "children": ["main-column"],
        },
        {
            "id": "main-column",
            "component": "MaterialColumn",
            "align": "stretch",
            "style": {"gap": "12px"},
            "children": ["header-row", "dashboard-frame", "actions-row"],
        },
        {
            "id": "header-row",
            "component": "MaterialRow",
            "justify": "spaceBetween",
            "align": "center",
            "children": ["title-col", "status-badge"],
        },
        {
            "id": "title-col",
            "component": "MaterialColumn",
            "children": ["title-text", "subtitle-text"],
        },
        {
            "id": "title-text",
            "component": "MaterialText",
            "text": title,
            "usageHint": "h2",
        },
        {
            "id": "subtitle-text",
            "component": "MaterialText",
            "text": f"Explore: {model_name}/{explore_name}" if model_name and explore_name else "Looker Embedded Analytics",
            "usageHint": "caption",
        },
        {
            "id": "status-badge",
            "component": "MaterialBadge",
            "text": status_text,
            "color": "primary",
            "children": ["badge-icon"],
        },
        {
            "id": "badge-icon",
            "component": "MaterialIcon",
            "icon": "verified",
        },
        {
            "id": "dashboard-frame",
            "component": "IFrameSrcdoc",
            "height": 750,
            "htmlContent": html_content,
        },
        {
            "id": "actions-row",
            "component": "MaterialRow",
            "justify": "spaceBetween",
            "align": "center",
            "children": ["folder-label", "button-group"],
        },
        {
            "id": "folder-label",
            "component": "MaterialText",
            "text": f"Folder: {folder_name or 'Personal / Shared'}",
            "usageHint": "caption",
        },
        {
            "id": "button-group",
            "component": "MaterialRow",
            "align": "center",
            "style": {"gap": "8px"},
            "children": ["btn-open-looker"],
        },
        {
            "id": "btn-open-looker",
            "component": "MaterialButton",
            "text": "Open in Looker",
            "color": "primary",
            "action": {
                "openUrl": {
                    "url": looker_url,
                }
            },
        },
    ]

    data_model = {
        "dashboard_id": dashboard_id,
        "slug": slug,
        "title": title,
        "embed_url": embed_url,
        "looker_url": looker_url,
        "folder_name": folder_name or "Personal / Shared",
        "tile_count": tile_count,
        "verified_count": verified_count,
    }

    return [
        {
            "version": "v0.9",
            "createSurface": {
                "surfaceId": surface_id,
                "catalogId": catalog_id,
                "theme": {
                    "primaryColor": "#1a73e8",
                    "font": "Google Sans",
                },
            },
        },
        {
            "version": "v0.9",
            "updateComponents": {
                "surfaceId": surface_id,
                "components": components,
            },
        },
        {
            "version": "v0.9",
            "updateDataModel": {
                "surfaceId": surface_id,
                "path": "/",
                "value": data_model,
            },
        },
    ]


def format_dashboard_markdown_response(
    dashboard_id: str,
    slug: str,
    title: str,
    embed_url: str,
    looker_url: str,
    folder_name: Optional[str] = None,
    tile_count: int = 0,
    verified_count: int = 0,
    a2ui_payload: Optional[Any] = None,
) -> str:
    """Formats a clean markdown response including direct links, summary, and A2UI embed markers."""
    lines = [
        f"### 📊 Dashboard Created: **{title}**",
        "",
        f"🔗 **[👉 Click here to Open Live Dashboard in Looker]({looker_url})**",
        "",
        f"- **Model & Explore**: LookML verified",
        f"- **Dashboard Slug**: `{slug}` (ID: `{dashboard_id}`)",
        f"- **Folder**: {folder_name or 'Personal / Shared'}",
        f"- **Verification Status**: ✅ {verified_count}/{tile_count} query tiles verified successfully against Looker",
        f"- **Signed Embed Link**: [Interactive Embed URL]({embed_url})",
        "",
        "---",
        "",
        "#### 🖼️ Live Embedded Dashboard View",
        "",
        f'<iframe src="{embed_url}" width="100%" height="750" frameborder="0" allowfullscreen></iframe>',
        "",
        "> [!TIP]",
        f"> You can refine this dashboard anytime by asking: *\"Add a breakdown tile by region or category to dashboard `{slug}`\"*.",
    ]

    return "\n".join(lines)

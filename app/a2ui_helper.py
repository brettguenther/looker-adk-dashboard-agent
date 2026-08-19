"""A2UI (Agent-to-User Interface) v0.9 Payload and Response Builder for Looker Dashboards."""

from __future__ import annotations

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
) -> Dict[str, Any]:
    """Constructs official A2UI v0.9 message envelope for Gemini Enterprise / Agentspace.

    Follows the A2UI v0.9 specification:
    - createSurface: initializes the rendering surface
    - updateComponents: flat adjacency list of native UI components
    - updateDataModel: state model for component bindings
    """
    surface_id = f"dashboard-surface-{slug}"
    catalog_id = "https://a2ui.org/catalogs/basic/0.9"

    subtitle = (
        f"Explore: {model_name}/{explore_name}"
        if model_name and explore_name
        else "Interactive Looker Dashboard"
    )
    status_text = (
        f"✅ {verified_count}/{tile_count} query tiles verified against live data"
        if tile_count > 0
        else "✅ Live Dashboard Deployed"
    )

    components: List[Dict[str, Any]] = [
        {
            "id": "root-card",
            "component": "Card",
            "props": {
                "title": title,
                "subtitle": subtitle,
            },
            "children": ["status-badge", "embed-iframe", "action-row"],
        },
        {
            "id": "status-badge",
            "component": "Text",
            "props": {
                "text": status_text,
                "variant": "caption",
            },
        },
        {
            "id": "embed-iframe",
            "component": "Iframe",
            "props": {
                "src": embed_url,
                "title": title,
                "height": "750px",
                "width": "100%",
                "style": {
                    "border": "1px solid #e0e0e0",
                    "borderRadius": "8px",
                    "marginTop": "12px",
                    "marginBottom": "12px",
                },
            },
        },
        {
            "id": "action-row",
            "component": "Row",
            "props": {
                "align": "end",
                "spacing": "small",
            },
            "children": ["btn-open-looker", "btn-refine"],
        },
        {
            "id": "btn-open-looker",
            "component": "Button",
            "props": {
                "label": "Open in Looker",
                "variant": "primary",
            },
            "action": {
                "type": "openUrl",
                "url": looker_url,
            },
        },
        {
            "id": "btn-refine",
            "component": "Button",
            "props": {
                "label": "Refine Dashboard",
                "variant": "secondary",
            },
            "action": {
                "type": "sendMessage",
                "prompt": f"Add a new metric tile to dashboard '{slug}'",
            },
        },
    ]

    data_model = {
        "dashboard_id": dashboard_id,
        "slug": slug,
        "title": title,
        "embed_url": embed_url,
        "looker_url": looker_url,
        "folder_name": folder_name or "Default / Shared",
        "tile_count": tile_count,
        "verified_count": verified_count,
    }

    return {
        "version": "v0.9",
        "createSurface": {
            "surfaceId": surface_id,
            "catalogId": catalog_id,
        },
        "updateComponents": {
            "surfaceId": surface_id,
            "components": components,
        },
        "updateDataModel": {
            "surfaceId": surface_id,
            "data": data_model,
        },
    }


def format_dashboard_markdown_response(
    dashboard_id: str,
    slug: str,
    title: str,
    embed_url: str,
    looker_url: str,
    folder_name: Optional[str] = None,
    tile_count: int = 0,
    verified_count: int = 0,
    a2ui_payload: Optional[Dict[str, Any]] = None,
) -> str:
    """Formats a clean markdown response including direct links, summary, and A2UI embed markers."""
    lines = [
        f"### 📊 Dashboard Created: **{title}**",
        "",
        f"🔗 **[👉 Click here to Open Live Dashboard in Looker]({looker_url})**",
        "",
        f"- **Dashboard Slug**: `{slug}` (ID: `{dashboard_id}`)",
        f"- **Folder**: {folder_name or 'Default / Shared'}",
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
        f"> You can refine this dashboard anytime by asking: *\"Add a new KPI card to dashboard `{slug}`\"*.",
    ]

    return "\n".join(lines)

"""A2UI Declarative UI and Iframe Embed Payload Builder for Looker Dashboards."""

from __future__ import annotations

from typing import Any, Dict, Optional


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
    """Constructs a declarative A2UI JSON card with an embedded iframe and action buttons."""
    return {
        "type": "a2ui_component",
        "version": "1.0",
        "component": {
            "type": "Card",
            "props": {
                "title": title,
                "subtitle": f"Looker Explore: {model_name}/{explore_name}" if model_name and explore_name else "Interactive Looker Dashboard",
                "badge": f"Verified ({verified_count}/{tile_count} tiles)" if tile_count > 0 else "Live Dashboard",
                "badgeColor": "success",
            },
            "children": [
                {
                    "type": "Iframe",
                    "props": {
                        "src": embed_url,
                        "title": title,
                        "height": "700px",
                        "width": "100%",
                        "allowFullScreen": True,
                        "sandbox": "allow-scripts allow-same-origin allow-forms allow-popups",
                        "style": {
                            "border": "1px solid #e0e0e0",
                            "borderRadius": "8px",
                            "boxShadow": "0 2px 8px rgba(0,0,0,0.05)",
                        },
                    },
                },
                {
                    "type": "ButtonGroup",
                    "props": {"align": "right", "spacing": "small"},
                    "children": [
                        {
                            "type": "Button",
                            "props": {
                                "label": "Open in Looker",
                                "variant": "primary",
                                "icon": "open_in_new",
                                "action": {
                                    "type": "open_url",
                                    "url": looker_url,
                                },
                            },
                        },
                        {
                            "type": "Button",
                            "props": {
                                "label": "Edit in Place",
                                "variant": "secondary",
                                "icon": "edit",
                                "action": {
                                    "type": "send_message",
                                    "prompt": f"Add a new tile to dashboard {slug}",
                                },
                            },
                        },
                    ],
                },
            ],
            "metadata": {
                "dashboard_id": dashboard_id,
                "slug": slug,
                "folder_name": folder_name or "Shared",
                "embed_url": embed_url,
                "looker_url": looker_url,
            },
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
        f"- **Direct Link**: [{title}]({looker_url})",
        f"- **Dashboard Slug**: `{slug}` (ID: `{dashboard_id}`)",
        f"- **Folder**: {folder_name or 'Default / Shared'}",
        f"- **Verification Status**: ✅ {verified_count}/{tile_count} query tiles verified successfully against Looker",
        "",
        "---",
        "",
        "#### 🖼️ Live Embedded Dashboard View",
        "",
        f'<iframe src="{embed_url}" width="100%" height="700" frameborder="0" allowfullscreen></iframe>',
        "",
        "> [!TIP]",
        f"> You can refine this dashboard anytime by asking: *\"Add a new KPI card to dashboard `{slug}`\"*.",
    ]

    return "\n".join(lines)

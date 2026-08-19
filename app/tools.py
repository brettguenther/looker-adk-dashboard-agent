"""ADK Function Tools for Looker Dashboard Architect Agent."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from google.adk.tools import ToolContext

from app.a2ui_helper import build_dashboard_a2ui_payload, format_dashboard_markdown_response
from app.generator import LookMLDashboardGenerator
from app.importer import dashboard_importer
from app.mcp_client import mcp_client
from app.verifier import dashboard_verifier

logger = logging.getLogger(__name__)

# Global generator instance
_generator = LookMLDashboardGenerator()


def list_available_models(tool_context: Optional[ToolContext] = None) -> List[Dict[str, Any]]:
    """List all available LookML models in the Looker instance.

    Returns:
        List of models with name, label, and explore details.
    """
    models = mcp_client.get_models(ctx=tool_context)
    return [{"name": m.get("name"), "label": m.get("label")} for m in models]


def list_explores_in_model(
    model_name: str,
    tool_context: Optional[ToolContext] = None,
) -> List[Dict[str, Any]]:
    """List all explores available within a specific LookML model.

    Args:
        model_name: The name of the LookML model (e.g. 'thelook').

    Returns:
        List of explores with name and label.
    """
    explores = mcp_client.get_explores(model_name, ctx=tool_context)
    return [{"name": e.get("name"), "label": e.get("label")} for e in explores]


def inspect_explore_schema(
    model_name: str,
    explore_name: str,
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """Retrieve full semantic schema (dimensions, measures, filters, parameters) for an Explore.

    Args:
        model_name: The name of the LookML model.
        explore_name: The name of the Explore (e.g. 'order_items').

    Returns:
        Dictionary containing verified dimensions, measures, filters, and parameters.
    """
    meta = mcp_client.get_explore_metadata(model_name, explore_name, ctx=tool_context)
    return {
        "model": model_name,
        "explore": explore_name,
        "measures": [{"name": m.get("name"), "type": m.get("type"), "label": m.get("label")} for m in meta.get("measures", [])],
        "dimensions": [{"name": d.get("name"), "type": d.get("type"), "label": d.get("label")} for d in meta.get("dimensions", [])[:35]],
        "filters": [{"name": f.get("name"), "label": f.get("label")} for f in meta.get("filters", [])],
        "parameters": [{"name": p.get("name"), "label": p.get("label")} for p in meta.get("parameters", [])],
    }


def query_looker_data(
    model: str,
    explore: str,
    fields: List[str],
    filters: Optional[Dict[str, Any]] = None,
    sorts: Optional[List[str]] = None,
    limit: int = 10,
    tool_context: Optional[ToolContext] = None,
) -> List[Any]:
    """Execute a live data query via Looker Managed MCP.

    Args:
        model: The LookML model name.
        explore: The LookML explore name.
        fields: List of fully-qualified dimension and measure names (e.g. ['users.country', 'order_items.total_revenue']).
        filters: Optional dictionary of filter expressions (e.g. {'orders.created_date': '30 days'}).
        sorts: Optional list of sort orders (e.g. ['order_items.total_revenue desc']).
        limit: Max number of rows to return.

    Returns:
        List of data row records returned from Looker.
    """
    return mcp_client.query(
        model=model,
        explore=explore,
        fields=fields,
        filters=filters,
        sorts=sorts,
        limit=limit,
        ctx=tool_context,
    )


def generate_lookml_dashboard(
    prompt: str,
    model_name: str,
    explore_name: str,
    title: str,
    preferred_slug: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Generate production-ready LookML Dashboard YAML grounded on verified Explore fields.

    Args:
        prompt: Business description of desired dashboard layout, charts, KPIs, and metrics.
        model_name: Target LookML model name.
        explore_name: Target Explore name.
        title: Proposed human-readable dashboard title.
        preferred_slug: Optional slug identifier for in-place updating of an existing dashboard.

    Returns:
        Complete, syntactically valid LookML dashboard YAML string.
    """
    meta = mcp_client.get_explore_metadata(model_name, explore_name, ctx=tool_context)
    return _generator.generate(
        prompt=prompt,
        explore_metadata=meta,
        dashboard_title=title,
        preferred_slug=preferred_slug,
    )


def verify_dashboard_queries(
    lookml_yaml: str,
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """Test all query-bearing tiles in LookML YAML against Looker Managed MCP before importing.

    Args:
        lookml_yaml: The candidate LookML dashboard YAML string to test.

    Returns:
        Verification report with pass/fail status, query errors, and latencies per tile.
    """
    report = dashboard_verifier.verify_lookml(lookml_yaml, ctx=tool_context)
    return {
        "all_passed": report.all_passed,
        "passed_count": report.passed_elements,
        "total_count": report.query_elements,
        "summary": report.format_summary(),
        "results": [
            {
                "element": r.element_name,
                "title": r.element_title,
                "type": r.element_type,
                "passed": r.passed,
                "error": r.error_message,
                "latency_ms": r.latency_ms,
            }
            for r in report.results
        ],
    }


def import_dashboard_lookml(
    lookml_yaml: str,
    folder_id: Optional[str] = None,
    preferred_slug: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """Import verified LookML YAML into Looker as an interactive User-Defined Dashboard (UDD).

    Args:
        lookml_yaml: Validated LookML dashboard YAML string.
        folder_id: Optional Looker folder ID where the dashboard should be created.
        preferred_slug: Optional slug for in-place update.

    Returns:
        Dictionary with dashboard id, title, slug, url, and folder details.
    """
    res = dashboard_importer.import_lookml(
        lookml_yaml=lookml_yaml,
        folder_id=folder_id,
        preferred_slug=preferred_slug,
        ctx=tool_context,
    )
    return {
        "id": res.id,
        "title": res.title,
        "slug": res.slug,
        "url": res.url,
        "folder_id": res.folder_id,
        "folder_name": res.folder_name,
    }


def run_dashboard(
    dashboard_id: str,
    filters: Optional[Dict[str, Any]] = None,
    tool_context: Optional[ToolContext] = None,
) -> Any:
    """Run an existing dashboard and fetch query results via Looker MCP.

    Args:
        dashboard_id: The ID or slug of the dashboard to run.
        filters: Optional runtime filter overrides.

    Returns:
        Dashboard run results and element data.
    """
    return mcp_client.run_dashboard(dashboard_id=dashboard_id, filters=filters, ctx=tool_context)


def generate_dashboard_embed_ui(
    dashboard_id_or_slug: str,
    title: str,
    model_name: Optional[str] = None,
    explore_name: Optional[str] = None,
    tile_count: int = 0,
    verified_count: int = 0,
    folder_name: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """Generate an embed URL and A2UI declarative iframe payload for the created dashboard.

    Args:
        dashboard_id_or_slug: Looker dashboard ID or slug.
        title: Human-readable dashboard title.
        model_name: LookML model name.
        explore_name: LookML explore name.
        tile_count: Total query tiles in the dashboard.
        verified_count: Number of tiles successfully verified.
        folder_name: Folder name where dashboard resides.

    Returns:
        Dictionary with embed_url, looker_url, a2ui_component payload, and markdown response.
    """
    embed_info = mcp_client.generate_embed_url(
        content_type="dashboards",
        content_id=str(dashboard_id_or_slug),
        ctx=tool_context,
    )
    embed_url = embed_info.get("url") or f"{dashboard_importer.instance_base_url}/embed/dashboards/{dashboard_id_or_slug}"
    looker_url = f"{dashboard_importer.instance_base_url}/dashboards/{dashboard_id_or_slug}"

    a2ui_payload = build_dashboard_a2ui_payload(
        dashboard_id=str(dashboard_id_or_slug),
        slug=str(dashboard_id_or_slug),
        title=title,
        embed_url=embed_url,
        looker_url=looker_url,
        folder_name=folder_name,
        tile_count=tile_count,
        verified_count=verified_count,
        model_name=model_name,
        explore_name=explore_name,
    )

    markdown_content = format_dashboard_markdown_response(
        dashboard_id=str(dashboard_id_or_slug),
        slug=str(dashboard_id_or_slug),
        title=title,
        embed_url=embed_url,
        looker_url=looker_url,
        folder_name=folder_name,
        tile_count=tile_count,
        verified_count=verified_count,
        a2ui_payload=a2ui_payload,
    )

    return {
        "embed_url": embed_url,
        "looker_url": looker_url,
        "a2ui_payload": a2ui_payload,
        "markdown_content": markdown_content,
    }

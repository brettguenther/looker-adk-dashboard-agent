"""Looker Managed MCP Client with dynamic OAuth authentication."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
import requests

from app.auth import get_auth_headers
from app.config import settings

logger = logging.getLogger(__name__)


class LookerManagedMCPClient:
    """Client for interacting with Looker Managed MCP Server (JSON-RPC over HTTP)."""

    def __init__(self, base_mcp_url: Optional[str] = None):
        self.mcp_url = (base_mcp_url or settings.mcp_url).rstrip("/")
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _post_jsonrpc(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        ctx: Optional[Any] = None,
    ) -> Dict[str, Any]:
        headers = get_auth_headers(ctx)
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or {},
        }
        logger.debug("POST %s (method: %s, id: %d)", self.mcp_url, method, payload["id"])
        resp = requests.post(
            self.mcp_url,
            headers=headers,
            json=payload,
            timeout=45,
            verify=settings.lookersdk_verify_ssl,
        )

        if resp.status_code == 401:
            logger.error("MCP request failed with 401 Unauthorized. Verify Looker OAuth credentials.")
            resp.raise_for_status()

        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            err = data["error"]
            raise RuntimeError(f"Looker MCP Error ({err.get('code')}): {err.get('message')}")
        return data.get("result", {})

    def list_tools(self, ctx: Optional[Any] = None) -> List[Dict[str, Any]]:
        """List all available tools exposed by Looker Managed MCP server."""
        res = self._post_jsonrpc("tools/list", {}, ctx=ctx)
        return res.get("tools", [])

    def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        ctx: Optional[Any] = None,
    ) -> List[Any]:
        """Call a Looker MCP tool and return parsed result contents."""
        res = self._post_jsonrpc("tools/call", {"name": name, "arguments": arguments or {}}, ctx=ctx)
        if res.get("isError"):
            err_msg = ""
            for item in res.get("content", []):
                err_msg += item.get("text", "")
            raise RuntimeError(f"Looker MCP tool '{name}' error: {err_msg}")

        contents = res.get("content", [])
        parsed_results: List[Any] = []
        for item in contents:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                try:
                    parsed = json.loads(text)
                    parsed_results.append(parsed)
                except Exception:
                    parsed_results.append(text)
            else:
                parsed_results.append(item)
        return parsed_results

    def get_models(self, ctx: Optional[Any] = None) -> List[Dict[str, Any]]:
        """List all available LookML models."""
        res = self.call_tool("get_models", {}, ctx=ctx)
        if res and isinstance(res[0], list):
            return res[0]
        return res

    def get_explores(self, model: str, ctx: Optional[Any] = None) -> List[Dict[str, Any]]:
        """List all explores within a model."""
        res = self.call_tool("get_explores", {"model": model}, ctx=ctx)
        if res and isinstance(res[0], list):
            return res[0]
        return res

    def get_dimensions(self, model: str, explore: str, ctx: Optional[Any] = None) -> List[Dict[str, Any]]:
        """List dimensions for an explore."""
        res = self.call_tool("get_dimensions", {"model": model, "explore": explore}, ctx=ctx)
        if res and isinstance(res[0], list):
            return res[0]
        return res

    def get_measures(self, model: str, explore: str, ctx: Optional[Any] = None) -> List[Dict[str, Any]]:
        """List measures for an explore."""
        res = self.call_tool("get_measures", {"model": model, "explore": explore}, ctx=ctx)
        if res and isinstance(res[0], list):
            return res[0]
        return res

    def get_filters(self, model: str, explore: str, ctx: Optional[Any] = None) -> List[Dict[str, Any]]:
        """List filter-only fields for an explore."""
        res = self.call_tool("get_filters", {"model": model, "explore": explore}, ctx=ctx)
        if res and isinstance(res[0], list):
            return res[0]
        return res

    def get_parameters(self, model: str, explore: str, ctx: Optional[Any] = None) -> List[Dict[str, Any]]:
        """List parameters for an explore."""
        res = self.call_tool("get_parameters", {"model": model, "explore": explore}, ctx=ctx)
        if res and isinstance(res[0], list):
            return res[0]
        return res

    def get_explore_metadata(self, model: str, explore: str, ctx: Optional[Any] = None) -> Dict[str, Any]:
        """Retrieve full metadata for an explore (dimensions, measures, filters, parameters)."""
        dims = self.get_dimensions(model, explore, ctx=ctx)
        meas = self.get_measures(model, explore, ctx=ctx)
        filters = self.get_filters(model, explore, ctx=ctx)
        params = self.get_parameters(model, explore, ctx=ctx)
        return {
            "model": model,
            "explore": explore,
            "dimensions": dims,
            "measures": meas,
            "filters": filters,
            "parameters": params,
        }

    def query(
        self,
        model: str,
        explore: str,
        fields: List[str],
        filters: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[str]] = None,
        limit: Optional[int] = 5,
        ctx: Optional[Any] = None,
    ) -> List[Any]:
        """Execute a query via Looker Managed MCP."""
        args: Dict[str, Any] = {
            "model": model,
            "explore": explore,
            "fields": fields,
        }
        if filters:
            args["filters"] = filters
        if sorts:
            args["sorts"] = sorts
        if limit is not None:
            try:
                args["limit"] = int(limit)
            except Exception:
                args["limit"] = 5

        res = self.call_tool("query", args, ctx=ctx)
        if res and isinstance(res[0], list):
            return res[0]
        return res

    def run_dashboard(
        self,
        dashboard_id: str,
        filters: Optional[Dict[str, Any]] = None,
        ctx: Optional[Any] = None,
    ) -> Any:
        """Run an existing dashboard and fetch element query results via Looker MCP."""
        args: Dict[str, Any] = {"id": str(dashboard_id)}
        if filters:
            args["filters"] = filters
        return self.call_tool("run_dashboard", args, ctx=ctx)

    def generate_embed_url(
        self,
        content_type: str = "dashboards",
        content_id: str = "",
        ctx: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Generate an embed URL for specific Looker content via Looker Managed MCP."""
        res = self.call_tool("generate_embed_url", {"type": content_type, "id": str(content_id)}, ctx=ctx)
        if res and isinstance(res[0], dict):
            return res[0]
        if res and isinstance(res[0], str):
            return {"url": res[0]}
        return {"url": f"{settings.lookersdk_base_url.rstrip('/')}/embed/{content_type}/{content_id}"}


mcp_client = LookerManagedMCPClient()

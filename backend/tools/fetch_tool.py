"""Fetch URL content via the official MCP fetch server on MCPD."""

from __future__ import annotations

from functools import lru_cache

from mcpd.mcp_client import MCPDClient


@lru_cache(maxsize=1)
def _client() -> MCPDClient:
    return MCPDClient()


def fetch_url(url: str, max_length: int = 5000) -> str:
    """Fetch and return readable content from a URL using the MCP fetch tool."""
    return _client().call_tool(
        "fetch",
        "fetch",
        {"url": url, "max_length": max_length},
    )

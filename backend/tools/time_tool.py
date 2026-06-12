"""Time tools backed by the mcpd time MCP server."""

from __future__ import annotations

from functools import lru_cache

from mcpd.mcp_client import MCPDClient


@lru_cache(maxsize=1)
def _client() -> MCPDClient:
    return MCPDClient()


def get_current_time(timezone: str) -> str:
    """Get the current date and time in a specific IANA timezone."""
    return _client().call_tool("time", "get_current_time", {"timezone": timezone})


def convert_time(source_timezone: str, time: str, target_timezone: str) -> str:
    """Convert a 24-hour time string from one timezone to another."""
    return _client().call_tool(
        "time",
        "convert_time",
        {
            "source_timezone": source_timezone,
            "time": time,
            "target_timezone": target_timezone,
        },
    )

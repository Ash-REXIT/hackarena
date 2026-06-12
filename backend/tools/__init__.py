"""Built-in and registered tool definitions."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mcpd.mcp_client import MCPDClient
from tools.document_tool import list_private_documents, search_private_documents
from tools.encoder_tool import analyze_text, classify_sentiment, get_text_embeddings
from tools.maps_tool import geocode_location
from tools.time_tool import convert_time, get_current_time
from tools.weather_tool import get_weather
from tools.web_tool import search_public_web

LOCAL_TOOL_BUILDERS: dict[str, Callable[[], Callable[..., str]]] = {
    "search_private_documents": lambda: search_private_documents,
    "list_private_documents": lambda: list_private_documents,
    "search_public_web": lambda: search_public_web,
    "get_current_time": lambda: get_current_time,
    "convert_time": lambda: convert_time,
    "get_weather": lambda: get_weather,
    "geocode_location": lambda: geocode_location,
    "analyze_text": lambda: analyze_text,
    "classify_sentiment": lambda: classify_sentiment,
    "get_text_embeddings": lambda: get_text_embeddings,
}

DEFAULT_LOCAL_TOOLS = [
    "search_private_documents",
    "list_private_documents",
    "search_public_web",
    "get_current_time",
    "convert_time",
    "get_weather",
    "geocode_location",
    "analyze_text",
    "classify_sentiment",
    "get_text_embeddings",
]
DEFAULT_ENABLED_LOCAL_TOOLS = [
    "search_private_documents",
    "list_private_documents",
    "search_public_web",
]

REGISTRY_PATH = Path(__file__).resolve().parent / "tools_registry.json"


class ToolRegistry:
    """Loads built-in tools plus user-added MCPD tool references."""

    def __init__(self, mcpd_client: MCPDClient, registry_path: Path = REGISTRY_PATH) -> None:
        self.mcpd_client = mcpd_client
        self.registry_path = registry_path
        self._entries = self._load_entries()

    def _load_entries(self) -> list[dict[str, Any]]:
        if not self.registry_path.exists():
            return self._default_entries()
        try:
            payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
            return payload.get("tools", self._default_entries())
        except json.JSONDecodeError:
            return self._default_entries()

    def _default_entries(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = [
            {"type": "local", "name": name, "enabled": True}
            for name in DEFAULT_ENABLED_LOCAL_TOOLS
        ]
        entries.extend(
            [
                {"type": "mcpd", "server": "time", "tool": "get_current_time", "enabled": True},
                {"type": "mcpd", "server": "time", "tool": "convert_time", "enabled": False},
            ]
        )
        return entries

    def get_tool_sources(self) -> dict[str, str]:
        sources: dict[str, str] = {}
        for entry in self._entries:
            if not entry.get("enabled", True):
                continue
            if entry.get("type") == "local":
                sources[entry["name"]] = "local"
            elif entry.get("type") == "mcpd":
                sources[entry["tool"]] = "mcpd"
        return sources

    def _save_entries(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(
            json.dumps({"tools": self._entries}, indent=2),
            encoding="utf-8",
        )

    def list_entries(self) -> list[dict[str, Any]]:
        return list(self._entries)

    def add_mcpd_tool(self, server: str, tool: str) -> dict[str, Any]:
        for entry in self._entries:
            if entry.get("type") == "mcpd" and entry.get("server") == server and entry.get("tool") == tool:
                entry["enabled"] = True
                self._save_entries()
                return entry

        entry = {
            "type": "mcpd",
            "server": server,
            "tool": tool,
            "enabled": True,
        }
        self._entries.append(entry)
        self._save_entries()
        return entry

    def add_local_tool(self, name: str) -> dict[str, Any]:
        if name not in LOCAL_TOOL_BUILDERS:
            raise ValueError(f"Unknown local tool: {name}")

        for entry in self._entries:
            if entry.get("type") == "local" and entry.get("name") == name:
                entry["enabled"] = True
                self._save_entries()
                return entry

        entry = {"type": "local", "name": name, "enabled": True}
        self._entries.append(entry)
        self._save_entries()
        return entry

    def remove_tool(self, tool_id: str) -> bool:
        before = len(self._entries)
        self._entries = [entry for entry in self._entries if self._entry_id(entry) != tool_id]
        if len(self._entries) == before:
            return False
        self._save_entries()
        return True

    def set_enabled(self, tool_id: str, enabled: bool) -> dict[str, Any] | None:
        for entry in self._entries:
            if self._entry_id(entry) == tool_id:
                entry["enabled"] = enabled
                self._save_entries()
                return entry
        return None

    @staticmethod
    def _entry_id(entry: dict[str, Any]) -> str:
        if entry.get("type") == "mcpd":
            return f"mcpd:{entry['server']}:{entry['tool']}"
        return f"local:{entry['name']}"

    def build_callables(self) -> list[Callable[..., str]]:
        callables: list[Callable[..., str]] = []

        for entry in self._entries:
            if not entry.get("enabled", True):
                continue

            if entry.get("type") == "local":
                builder = LOCAL_TOOL_BUILDERS.get(entry["name"])
                if builder:
                    callables.append(builder())
                continue

            if entry.get("type") == "mcpd":
                server = entry["server"]
                tool_name = entry["tool"]
                tool_defs = self.mcpd_client.list_server_tools(server)
                tool_def = next((item for item in tool_defs if item["name"] == tool_name), None)
                if not tool_def:
                    continue
                callables.append(
                    self.mcpd_client.create_tool_callable(
                        server=server,
                        tool_name=tool_name,
                        description=tool_def.get("description", ""),
                        input_schema=tool_def.get("inputSchema"),
                    )
                )

        return callables

    def describe_tools(self) -> list[dict[str, Any]]:
        descriptions: list[dict[str, Any]] = []

        for entry in self._entries:
            tool_id = self._entry_id(entry)
            if entry.get("type") == "local":
                fn = LOCAL_TOOL_BUILDERS[entry["name"]]()
                descriptions.append(
                    {
                        "id": tool_id,
                        "type": "local",
                        "name": entry["name"],
                        "enabled": entry.get("enabled", True),
                        "description": (fn.__doc__ or "").strip(),
                    }
                )
                continue

            if entry.get("type") == "mcpd":
                try:
                    tool_defs = self.mcpd_client.list_server_tools(entry["server"])
                    tool_def = next(
                        (item for item in tool_defs if item["name"] == entry["tool"]),
                        None,
                    )
                    description = tool_def.get("description", "") if tool_def else ""
                except Exception as exc:  # noqa: BLE001
                    description = f"Unavailable: {exc}"
                descriptions.append(
                    {
                        "id": tool_id,
                        "type": "mcpd",
                        "server": entry["server"],
                        "name": entry["tool"],
                        "enabled": entry.get("enabled", True),
                        "description": description,
                    }
                )

        return descriptions

    def list_mcpd_catalog(self) -> list[dict[str, Any]]:
        catalog: list[dict[str, Any]] = []
        for server in self.mcpd_client.list_servers():
            for tool_def in self.mcpd_client.list_server_tools(server):
                catalog.append(
                    {
                        "server": server,
                        "name": tool_def["name"],
                        "description": tool_def.get("description", ""),
                    }
                )
        return catalog

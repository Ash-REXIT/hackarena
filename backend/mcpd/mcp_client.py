"""Reusable MCPD HTTP client for calling MCP tools exposed by mcpd."""

from __future__ import annotations

import inspect
from typing import Any, Callable

import requests

from mcpd.constants import DEFAULT_MCPD_BASE_URL, MCPD_API_PREFIX


class MCPDClient:
    """Client for the mcpd daemon HTTP API."""

    def __init__(self, base_url: str = DEFAULT_MCPD_BASE_URL, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def api_root(self) -> str:
        return f"{self.base_url}{MCPD_API_PREFIX}"

    def list_servers(self) -> list[str]:
        response = requests.get(f"{self.api_root}/servers", timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def list_server_tools(self, server: str) -> list[dict[str, Any]]:
        response = requests.get(
            f"{self.api_root}/servers/{server}/tools",
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("tools", payload if isinstance(payload, list) else [])

    def call_tool(self, server: str, tool: str, arguments: dict[str, Any]) -> str:
        response = requests.post(
            f"{self.api_root}/servers/{server}/tools/{tool}",
            json=arguments,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.text

    def create_tool_callable(
        self,
        server: str,
        tool_name: str,
        description: str,
        input_schema: dict[str, Any] | None = None,
    ) -> Callable[..., str]:
        properties = (input_schema or {}).get("properties", {})
        required = set((input_schema or {}).get("required", []))

        parameters: list[inspect.Parameter] = []
        annotations: dict[str, Any] = {"return": str}

        for param_name, param_info in properties.items():
            param_type = str if param_info.get("type") == "string" else Any
            annotations[param_name] = param_type
            if param_name in required:
                parameters.append(
                    inspect.Parameter(
                        param_name,
                        inspect.Parameter.KEYWORD_ONLY,
                        annotation=param_type,
                    )
                )
            else:
                parameters.append(
                    inspect.Parameter(
                        param_name,
                        inspect.Parameter.KEYWORD_ONLY,
                        default=None,
                        annotation=param_type | None,
                    )
                )

        def tool_function(**kwargs: Any) -> str:
            clean_args = {key: value for key, value in kwargs.items() if value is not None}
            return self.call_tool(server, tool_name, clean_args)

        tool_function.__name__ = tool_name
        tool_function.__doc__ = description or f"MCPD tool {server}/{tool_name}"
        tool_function.__signature__ = inspect.Signature(parameters, return_annotation=str)  # type: ignore[attr-defined]
        tool_function.__annotations__ = annotations
        return tool_function

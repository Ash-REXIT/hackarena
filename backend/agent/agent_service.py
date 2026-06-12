"""Creates and runs the Any-Agent backed by local llamafile + MCPD tools."""

from __future__ import annotations

from typing import Any

from any_agent import AgentConfig, AgentFramework, AnyAgent

from agent.config import get_settings
from agent.prompts import SYSTEM_PROMPT
from mcpd.mcp_client import MCPDClient
from tools import ToolRegistry


class AgentService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.mcpd_client = MCPDClient(base_url=self.settings.mcpd_base_url)
        self.tool_registry = ToolRegistry(self.mcpd_client)
        self._agent: AnyAgent | None = None

    async def _build_agent(self) -> AnyAgent:
        tools = self.tool_registry.build_callables()
        config = AgentConfig(
            model_id=self.settings.llm_model_id,
            api_base=self.settings.llm_api_base,
            api_key=self.settings.llm_api_key,
            tools=tools,
            instructions=SYSTEM_PROMPT,
            model_args={"temperature": 0.1},
        )
        return await AnyAgent.create_async(
            agent_framework=AgentFramework.OPENAI,
            agent_config=config,
        )

    async def reload_agent(self) -> None:
        self._agent = await self._build_agent()

    async def run_query(self, query: str) -> dict[str, Any]:
        if not self._agent:
            await self.reload_agent()

        assert self._agent is not None
        trace = await self._agent.run_async(query)
        final_output = trace.final_output
        if final_output is None:
            messages = trace.spans_to_messages()
            final_output = messages[-1].content if messages else "No response generated."
        elif not isinstance(final_output, str):
            final_output = str(final_output)

        spans_summary = []
        if hasattr(trace, "spans"):
            for span in trace.spans:
                spans_summary.append(
                    {
                        "name": span.name,
                        "status": getattr(span.status.status_code, "name", str(span.status.status_code)),
                    }
                )

        return {
            "response": final_output,
            "trace": spans_summary,
            "tools_used": [item["name"] for item in spans_summary if "tool" in item["name"].lower()],
        }

    def health(self) -> dict[str, Any]:
        llm_ok = False
        mcpd_ok = False
        llm_error = ""
        mcpd_error = ""

        try:
            import requests

            response = requests.get(f"{self.settings.llm_api_base}/models", timeout=5)
            llm_ok = response.ok
        except Exception as exc:  # noqa: BLE001
            llm_error = str(exc)

        try:
            self.mcpd_client.list_servers()
            mcpd_ok = True
        except Exception as exc:  # noqa: BLE001
            mcpd_error = str(exc)

        return {
            "llm": {"ok": llm_ok, "api_base": self.settings.llm_api_base, "error": llm_error},
            "mcpd": {"ok": mcpd_ok, "base_url": self.settings.mcpd_base_url, "error": mcpd_error},
            "model_id": self.settings.llm_model_id,
        }


agent_service = AgentService()

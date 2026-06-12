"""Creates and runs the Any-Agent backed by local llamafile + MCPD tools."""

from __future__ import annotations

import json
from typing import Any

from any_agent import AgentConfig, AgentFramework, AnyAgent
from any_agent.tracing.attributes import GenAI

from agent.config import get_settings
from agent.privatelens import PrivateLensPipeline
from agent.problem import PROBLEM_INSTRUCTIONS
from agent.prompts import SYSTEM_PROMPT
from agent.usage_tracker import usage_tracker
from encoder.encoder_client import EncoderfileClient
from mcpd.mcp_client import MCPDClient
from tools import ToolRegistry


def normalize_response_text(text: str) -> str:
    """Convert literal \\n from small LLMs into real line breaks."""
    if not text:
        return text
    cleaned = text.replace("\\n", "\n").replace("\\t", "\t").strip()
    return cleaned


class AgentService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.mcpd_client = MCPDClient(base_url=self.settings.mcpd_base_url)
        self.encoder_client = EncoderfileClient(base_url=self.settings.encoderfile_base_url)
        self.tool_registry = ToolRegistry(self.mcpd_client)
        self._agent: AnyAgent | None = None

    async def _build_agent(self) -> AnyAgent:
        tools = self.tool_registry.build_callables()
        config = AgentConfig(
            model_id=self.settings.llm_model_id,
            api_base=self.settings.llm_api_base,
            api_key=self.settings.llm_api_key,
            tools=tools,
            instructions=f"{SYSTEM_PROMPT}\n\n{PROBLEM_INSTRUCTIONS}".strip(),
            model_args={"temperature": 0.1, "parallel_tool_calls": False},
        )
        return await AnyAgent.create_async(
            agent_framework=AgentFramework.OPENAI,
            agent_config=config,
        )

    async def reload_agent(self) -> None:
        self._agent = await self._build_agent()

    def _extract_tool_usage(self, trace: Any) -> dict[str, Any]:
        tool_sources = self.tool_registry.get_tool_sources()
        tool_calls: list[dict[str, Any]] = []
        mcp_tools_used: list[str] = []
        local_tools_used: list[str] = []

        if not hasattr(trace, "spans"):
            return {
                "tool_calls": tool_calls,
                "tools_used": [],
                "mcp_tools_used": mcp_tools_used,
                "local_tools_used": local_tools_used,
            }

        seen: set[str] = set()
        for span in trace.spans:
            if not span.is_tool_execution():
                continue

            tool_name = span.attributes.get(GenAI.TOOL_NAME, span.name)
            if tool_name in seen:
                continue
            seen.add(tool_name)

            source = tool_sources.get(tool_name, "unknown")
            args_raw = span.attributes.get(GenAI.TOOL_ARGS, "{}")
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except json.JSONDecodeError:
                args = {"raw": args_raw}

            output = span.get_output_content()
            entry = {
                "name": tool_name,
                "source": source,
                "args": args,
                "output_preview": (output or "")[:240],
            }
            tool_calls.append(entry)

            if source == "mcpd":
                mcp_tools_used.append(tool_name)
                usage_tracker.record_mcp_call()
            elif source == "local":
                local_tools_used.append(tool_name)

        return {
            "tool_calls": tool_calls,
            "tools_used": [item["name"] for item in tool_calls],
            "mcp_tools_used": mcp_tools_used,
            "local_tools_used": local_tools_used,
        }

    async def run_query(self, query: str) -> dict[str, Any]:
        if not self._agent:
            await self.reload_agent()

        pipeline = PrivateLensPipeline()
        matches, confidence, boundary, encoder_status = pipeline.run_retrieval(query)
        decision = pipeline.run_decision(query, confidence, matches, boundary)
        local_context = pipeline.run_local_stage(matches, live_data=decision["live_data"])
        web_context, web_used = pipeline.run_web_stage(query, decision["use_web"], matches)

        answer_prompt = PrivateLensPipeline.build_answer_prompt(
            query=query,
            local_context=local_context,
            web_context=web_context,
            confidence=confidence,
            decision_reason=decision["reason"],
            live_data=decision["live_data"],
        )

        assert self._agent is not None
        trace = await self._agent.run_async(answer_prompt, max_turns=6)
        final_output = trace.final_output
        if final_output is None:
            messages = trace.spans_to_messages()
            assistant_messages = [
                message.content
                for message in messages
                if getattr(message, "role", "") == "assistant" and message.content
            ]
            final_output = assistant_messages[-1] if assistant_messages else "No response generated."
        elif not isinstance(final_output, str):
            final_output = str(final_output)

        final_output = normalize_response_text(final_output)

        usage = self._extract_tool_usage(trace)
        spans_summary = []
        if hasattr(trace, "spans"):
            for span in trace.spans:
                spans_summary.append(
                    {
                        "name": span.name,
                        "status": getattr(span.status.status_code, "name", str(span.status.status_code)),
                    }
                )

        metadata = pipeline.finalize_metadata(
            query=query,
            matches=matches,
            confidence=confidence,
            boundary=boundary,
            decision=decision,
            web_used=web_used,
            web_context=web_context,
            mcp_tools=usage["mcp_tools_used"],
            local_tools=usage["local_tools_used"],
            encoder_status=encoder_status,
            tool_calls=usage["tool_calls"],
        )

        return {
            "response": final_output,
            "trace": spans_summary,
            **usage,
            **metadata,
        }

    def health(self) -> dict[str, Any]:
        llm_ok = False
        mcpd_ok = False
        encoder_ok = False
        llm_error = ""
        mcpd_error = ""
        encoder_error = ""
        encoder_model: dict[str, Any] = {}

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

        try:
            encoder_ok = self.encoder_client.health()
            encoder_model = self.encoder_client.model_info()
        except Exception as exc:  # noqa: BLE001
            encoder_error = str(exc)

        from documents.store import list_documents_with_meta, get_encoder_retrieval_status

        return {
            "app": "FoxZilla",
            "tagline": "Your Documents First. The Internet Second.",
            "llm": {"ok": llm_ok, "api_base": self.settings.llm_api_base, "error": llm_error},
            "encoderfile": {
                "ok": encoder_ok,
                "base_url": self.settings.encoderfile_base_url,
                "model": encoder_model,
                "error": encoder_error,
                "retrieval": get_encoder_retrieval_status(),
            },
            "mcpd": {"ok": mcpd_ok, "base_url": self.settings.mcpd_base_url, "error": mcpd_error},
            "private_docs": list_documents_with_meta(),
            "model_id": self.settings.llm_model_id,
            "internet_budget": usage_tracker.as_dict(),
            "ready": llm_ok and mcpd_ok,
        }


agent_service = AgentService()

"""Creates and runs the Any-Agent backed by local llamafile + MCPD tools."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from any_agent import AgentConfig, AgentFramework, AnyAgent
from any_agent.tracing.attributes import GenAI

from agent.config import get_settings
from agent.job_status import job_tracker
from agent.privatelens import PrivateLensPipeline
from agent.problem import PROBLEM_INSTRUCTIONS
from agent.prompts import SYSTEM_PROMPT
from agent.usage_tracker import usage_tracker
from encoder.encoder_client import EncoderfileClient
from mcpd.mcp_client import MCPDClient
from tools import ToolRegistry
from tools.web_tool import needs_fresh_web_query, try_fresh_web_direct_answer, try_wikipedia_direct_answer


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
        self._last_query: str = ""

    async def _build_agent(self) -> AnyAgent:
        from agent.runtime_settings import runtime_settings

        tools = self.tool_registry.build_callables()
        temperature = runtime_settings.snapshot()["temperature"]
        config = AgentConfig(
            model_id=self.settings.llm_model_id,
            api_base=self.settings.llm_api_base,
            api_key=self.settings.llm_api_key,
            tools=tools,
            instructions=f"{SYSTEM_PROMPT}\n\n{PROBLEM_INSTRUCTIONS}".strip(),
            model_args={"temperature": temperature, "parallel_tool_calls": False},
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

    def _run_pipeline_blocking(self, query: str) -> dict[str, Any]:
        """Run sync pipeline stages without blocking the asyncio event loop."""
        pipeline = PrivateLensPipeline()
        job_tracker.set_stage("retrieval")
        matches, confidence, boundary, encoder_status = pipeline.run_retrieval(query)
        job_tracker.set_stage("decision")
        decision = pipeline.run_decision(query, confidence, matches, boundary)
        job_tracker.set_stage("local")
        local_context = pipeline.run_local_stage(
            matches,
            live_data=decision["live_data"],
            fetch_url=decision.get("fetch_url", False),
        )
        job_tracker.set_stage("web")
        web_context, web_used = pipeline.run_web_stage(query, decision["use_web"], matches)
        answer_prompt = PrivateLensPipeline.build_answer_prompt(
            query=query,
            local_context=local_context,
            web_context=web_context,
            confidence=confidence,
            decision_reason=decision["reason"],
            live_data=decision["live_data"],
            fetch_url=decision.get("fetch_url", False),
        )
        return {
            "pipeline": pipeline,
            "matches": matches,
            "confidence": confidence,
            "boundary": boundary,
            "encoder_status": encoder_status,
            "decision": decision,
            "web_used": web_used,
            "web_context": web_context,
            "answer_prompt": answer_prompt,
        }

    def _build_result_from_trace(
        self,
        *,
        query: str,
        ctx: dict[str, Any],
        trace: Any,
    ) -> dict[str, Any]:
        pipeline: PrivateLensPipeline = ctx["pipeline"]
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
            matches=ctx["matches"],
            confidence=ctx["confidence"],
            boundary=ctx["boundary"],
            decision=ctx["decision"],
            web_used=ctx["web_used"],
            web_context=ctx["web_context"],
            mcp_tools=usage["mcp_tools_used"],
            local_tools=usage["local_tools_used"],
            encoder_status=ctx["encoder_status"],
            tool_calls=usage["tool_calls"],
        )

        return {
            "response": final_output,
            "trace": spans_summary,
            **usage,
            **metadata,
        }

    def _build_result_from_direct_answer(
        self,
        *,
        query: str,
        ctx: dict[str, Any],
        response_text: str,
    ) -> dict[str, Any]:
        pipeline: PrivateLensPipeline = ctx["pipeline"]
        metadata = pipeline.finalize_metadata(
            query=query,
            matches=ctx["matches"],
            confidence=ctx["confidence"],
            boundary=ctx["boundary"],
            decision=ctx["decision"],
            web_used=ctx["web_used"],
            web_context=ctx["web_context"],
            mcp_tools=[],
            local_tools=[],
            encoder_status=ctx["encoder_status"],
            tool_calls=[],
        )
        pipeline._set_agent("Answer Agent", "complete", "Wikipedia direct answer")
        pipeline._add_timeline(
            "Answer from live web extraction (LLM skipped for current-role reliability)",
            "Answer Agent",
        )
        metadata["agents"] = pipeline.agent_status
        metadata["timeline"] = pipeline.timeline
        return {
            "response": response_text,
            "trace": [{"name": "web_direct", "status": "OK"}],
            "tool_calls": [],
            "tools_used": [],
            "mcp_tools_used": [],
            "local_tools_used": [],
            **metadata,
        }

    async def run_query(self, query: str, request_id: str = "") -> dict[str, Any]:
        from documents.store import compound_query_needs_web, expand_meta_followup, is_meta_followup_query

        effective_query = expand_meta_followup(query, self._last_query or None)
        if not is_meta_followup_query(query):
            self._last_query = query

        if request_id:
            job_tracker.set_query(effective_query)
        else:
            job_tracker.start(effective_query, request_id=request_id)
        try:
            if not self._agent:
                await self.reload_agent()

            loop = asyncio.get_running_loop()
            ctx = await loop.run_in_executor(None, self._run_pipeline_blocking, effective_query)

            decision = ctx["decision"]
            hybrid = ctx["web_used"] and compound_query_needs_web(effective_query, ctx["matches"])

            def _try_direct_answer() -> str | None:
                if needs_fresh_web_query(effective_query):
                    return try_fresh_web_direct_answer(effective_query)
                if not hybrid:
                    return try_wikipedia_direct_answer(effective_query)
                return None

            if (
                ctx["web_used"]
                and not decision.get("live_data")
                and not decision.get("fetch_url")
            ):
                direct = await loop.run_in_executor(None, _try_direct_answer)
                if direct:
                    job_tracker.set_stage("finalize")
                    result = self._build_result_from_direct_answer(
                        query=effective_query,
                        ctx=ctx,
                        response_text=direct,
                    )
                    job_tracker.complete(result)
                    return result

            job_tracker.set_stage("answer_agent")
            assert self._agent is not None
            trace = await self._agent.run_async(
                ctx["answer_prompt"],
                max_turns=self.settings.llm_max_turns,
            )

            job_tracker.set_stage("finalize")
            result = self._build_result_from_trace(query=effective_query, ctx=ctx, trace=trace)
            job_tracker.complete(result)
            return result
        except Exception as exc:  # noqa: BLE001
            job_tracker.fail(str(exc))
            raise

    def get_job_status(self) -> dict[str, Any]:
        return job_tracker.snapshot()

    def health(self, *, fast: bool = False) -> dict[str, Any]:
        """Check stack health. Use fast=True for navbar polls (short timeouts)."""
        timeout = 2 if fast else 5
        llm_ok = False
        mcpd_ok = False
        encoder_ok = False
        llm_error = ""
        mcpd_error = ""
        encoder_error = ""
        encoder_model: dict[str, Any] = {}

        try:
            import requests

            response = requests.get(f"{self.settings.llm_api_base}/models", timeout=timeout)
            llm_ok = response.ok
        except Exception as exc:  # noqa: BLE001
            llm_error = str(exc)

        try:
            response = requests.get(
                f"{self.mcpd_client.api_root}/servers",
                timeout=timeout,
            )
            mcpd_ok = response.ok
        except Exception as exc:  # noqa: BLE001
            mcpd_error = str(exc)

        try:
            from encoder.encoder_client import EncoderfileClient

            client = EncoderfileClient(timeout=3)
            encoder_ok = client.health()
            if not fast:
                encoder_model = self.encoder_client.model_info()
        except Exception as exc:  # noqa: BLE001
            encoder_error = str(exc)

        from documents.store import list_documents_with_meta
        from agent.runtime_settings import runtime_settings

        retrieval = {"retrieval_mode": "keyword", "message": "Encoderfile status deferred"}
        if not fast:
            from documents.store import get_encoder_retrieval_status

            retrieval = get_encoder_retrieval_status()

        return {
            "app": "FoxZilla",
            "tagline": "Your Documents First. The Internet Second.",
            "llm": {
                "ok": llm_ok,
                "api_base": self.settings.llm_api_base,
                "max_turns": self.settings.llm_max_turns,
                "error": llm_error,
            },
            "encoderfile": {
                "ok": encoder_ok,
                "base_url": self.settings.encoderfile_base_url,
                "model": encoder_model,
                "error": encoder_error,
                "retrieval": retrieval,
            },
            "mcpd": {"ok": mcpd_ok, "base_url": self.settings.mcpd_base_url, "error": mcpd_error},
            "private_docs": list_documents_with_meta() if not fast else [],
            "model_id": self.settings.llm_model_id,
            "internet_budget": usage_tracker.as_dict(),
            "settings": runtime_settings.snapshot(),
            "stack": {
                "llamafile": {"ok": llm_ok, "port": 8080},
                "encoderfile": {"ok": encoder_ok, "port": 8081},
                "mcpd": {"ok": mcpd_ok, "port": 8090},
                "any_agent": {"framework": "any-agent", "port": self.settings.port},
            },
            "ready": llm_ok and encoder_ok and mcpd_ok,
        }


agent_service = AgentService()

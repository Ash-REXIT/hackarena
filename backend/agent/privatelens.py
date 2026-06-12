"""PrivateLens AI multi-agent pipeline orchestration."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from agent.usage_tracker import usage_tracker
from documents.store import (
    DocumentChunk,
    compute_confidence,
    get_encoder_retrieval_status,
    is_live_data_query,
    list_documents,
    search_documents,
    should_use_web,
)
from tools.web_tool import search_public_web


def _now_label() -> str:
    return datetime.now().strftime("%H:%M:%S")


class PrivateLensPipeline:
    """Runs Retriever → Confidence → Decision → Local/Web → Answer stages."""

    AGENTS = (
        "Retriever Agent",
        "Confidence Agent",
        "Decision Agent",
        "Local Agent",
        "Web Agent",
        "Answer Agent",
    )

    def __init__(self) -> None:
        self.timeline: list[dict[str, str]] = []
        self.agent_status: list[dict[str, Any]] = []

    def _add_timeline(self, event: str, agent: str) -> None:
        self.timeline.append({"time": _now_label(), "event": event, "agent": agent})

    def _set_agent(self, name: str, status: str, detail: str = "") -> None:
        for item in self.agent_status:
            if item["name"] == name:
                item["status"] = status
                item["detail"] = detail
                return
        self.agent_status.append({"name": name, "status": status, "detail": detail})

    def _init_agents(self) -> None:
        self.agent_status = [
            {"name": "Retriever Agent", "status": "pending", "detail": ""},
            {"name": "Confidence Agent", "status": "pending", "detail": ""},
            {"name": "Decision Agent", "status": "pending", "detail": ""},
            {"name": "Local Agent", "status": "pending", "detail": ""},
            {"name": "Web Agent", "status": "pending", "detail": ""},
            {"name": "Answer Agent", "status": "pending", "detail": ""},
        ]

    def run_retrieval(self, query: str) -> tuple[list[DocumentChunk], int, str, dict[str, Any]]:
        self._init_agents()
        self._set_agent("Retriever Agent", "active", "Searching local knowledge base")
        self._add_timeline("Searching Local Documents", "Retriever Agent")

        encoder_status = get_encoder_retrieval_status()
        self._add_timeline(encoder_status["message"], "Retriever Agent · Encoderfile")

        matches = search_documents(query)
        search_methods = sorted({m.search_method for m in matches}) if matches else ["none"]
        self._add_timeline(
            f"Retrieval mode: {encoder_status.get('retrieval_mode', 'keyword')} "
            f"({', '.join(search_methods)})",
            "Retriever Agent · Encoderfile",
        )
        count = len(matches)
        self._add_timeline(f"Found {count} Match{'es' if count != 1 else ''}", "Retriever Agent")
        self._set_agent("Retriever Agent", "complete", f"{count} matches")

        self._set_agent("Confidence Agent", "active", "Analyzing retrieval quality")
        confidence = compute_confidence(matches)
        self._add_timeline(f"Confidence = {confidence}%", "Confidence Agent")
        self._set_agent("Confidence Agent", "complete", f"{confidence}%")

        boundary = "found_locally" if matches and (confidence >= 50 or matches[0].score >= 0.35) else "not_found_locally"
        if not matches:
            boundary = "not_found_locally"

        return matches, confidence, boundary, encoder_status

    def run_decision(
        self,
        query: str,
        confidence: int,
        matches: list[DocumentChunk],
        boundary: str,
    ) -> dict[str, Any]:
        self._set_agent("Decision Agent", "active", "Evaluating internet need")
        use_web = should_use_web(confidence, query, matches)
        live_data = is_live_data_query(query)

        if live_data:
            use_web = False
            reason = "Live time query — MCP tools preferred over web search."
            self._add_timeline("Internet Search Skipped (MCP time tool)", "Decision Agent")
            self._set_agent("Web Agent", "skipped", "MCP handles live time")
        elif use_web:
            reason = "Local confidence low or query needs fresh public information."
            self._add_timeline("Internet Search Required", "Decision Agent")
        else:
            reason = "Local confidence high. Internet not required."
            self._add_timeline("Internet Search Skipped", "Decision Agent")
            self._set_agent("Web Agent", "skipped", "Local docs sufficient")

        self._set_agent("Decision Agent", "complete", reason)
        return {
            "use_web": use_web,
            "live_data": live_data,
            "reason": reason,
            "boundary": boundary,
        }

    def run_local_stage(self, matches: list[DocumentChunk]) -> str:
        self._set_agent("Local Agent", "active", "Preparing local evidence")
        if not matches:
            self._set_agent("Local Agent", "complete", "No local matches")
            return "No relevant local documents found."
        lines = ["Local document evidence:"]
        for index, match in enumerate(matches, start=1):
            lines.append(f"{index}. [{match.source}] (confidence {match.score:.0%}, {match.search_method})")
            lines.append(f'   "{match.text}"')
        context = "\n".join(lines)
        self._set_agent("Local Agent", "complete", f"{len(matches)} sources")
        return context

    def run_web_stage(self, query: str, use_web: bool) -> tuple[str | None, bool]:
        if not use_web:
            return None, False

        self._set_agent("Web Agent", "active", "Searching public internet")
        self._add_timeline("Searching Internet...", "Web Agent")
        web_result = search_public_web(query)
        usage_tracker.record_web_search()
        self._add_timeline("Web Search Complete", "Web Agent")
        self._set_agent("Web Agent", "complete", "Public sources retrieved")
        return web_result, True

    @staticmethod
    def build_answer_prompt(
        query: str,
        local_context: str,
        web_context: str | None,
        confidence: int,
        decision_reason: str,
        live_data: bool,
    ) -> str:
        sections = [
            "You are the Answer Agent in PrivateLens AI.",
            "Trust local documents first. Cite document names when using local evidence.",
            "Give one clear, concise final answer.",
            "",
            f"User question: {query}",
            f"Local confidence: {confidence}%",
            f"Decision: {decision_reason}",
            "",
            local_context,
        ]
        if web_context:
            sections.extend(["", web_context])
        if live_data:
            sections.extend(
                [
                    "",
                    "This is a live time/timezone question. Call get_current_time MCP tool if needed.",
                ]
            )
        sections.extend(
            [
                "",
                "State whether the answer came from local documents, web verification, or MCP tools.",
            ]
        )
        return "\n".join(sections)

    @staticmethod
    def build_evidence(matches: list[DocumentChunk]) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        for match in matches:
            info = None
            try:
                from documents.store import get_document_info

                info = get_document_info(match.source)
            except Exception:  # noqa: BLE001
                pass
            evidence.append(
                {
                    "document": match.source,
                    "chunk_id": match.chunk_id,
                    "excerpt": match.text,
                    "score": round(match.score * 100),
                    "search_method": match.search_method,
                    "freshness": info.freshness_label if info else "Unknown",
                    "modified_at": info.modified_at if info else None,
                }
            )
        return evidence

    @staticmethod
    def compute_privacy_score(
        *,
        web_used: bool,
        mcp_tools: list[str],
        local_used: bool,
    ) -> tuple[int, str]:
        if web_used:
            return 35, "Internet search required for this answer."
        if mcp_tools:
            return 85, "MCP live tool used. No web search."
        if local_used:
            return 100, "No internet used. Entire answer generated locally."
        return 90, "Answer generated locally without web search."

    @staticmethod
    def compute_source_breakdown(
        *,
        confidence: int,
        web_used: bool,
        mcp_tools: list[str],
        matches: list[DocumentChunk] | None = None,
    ) -> dict[str, int]:
        if web_used:
            if not matches:
                return {"local_documents": 0, "web_verification": 100, "mcp_tools": 0}
            top_score = matches[0].score
            if top_score < 0.35 or confidence < 35:
                return {"local_documents": 0, "web_verification": 100, "mcp_tools": 0}
            local_pct = min(50, max(5, int(top_score * 100)))
            return {
                "local_documents": local_pct,
                "web_verification": 100 - local_pct,
                "mcp_tools": 0,
            }
        if mcp_tools:
            return {"local_documents": 0, "web_verification": 0, "mcp_tools": 100}
        return {"local_documents": 100, "web_verification": 0, "mcp_tools": 0}

    def finalize_metadata(
        self,
        *,
        query: str,
        matches: list[DocumentChunk],
        confidence: int,
        boundary: str,
        decision: dict[str, Any],
        web_used: bool,
        web_context: str | None,
        mcp_tools: list[str],
        local_tools: list[str],
        encoder_status: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._add_timeline("Generating Answer", "Answer Agent")
        self._set_agent("Answer Agent", "complete", "Response synthesized")

        privacy_score, privacy_reason = self.compute_privacy_score(
            web_used=web_used,
            mcp_tools=mcp_tools,
            local_used=bool(matches),
        )
        source_breakdown = self.compute_source_breakdown(
            confidence=confidence,
            web_used=web_used,
            mcp_tools=mcp_tools,
            matches=matches,
        )

        documents_used = sorted({match.source for match in matches})
        local_sources = [{"name": name, "type": "local"} for name in documents_used]
        internet_sources: list[dict[str, str]] = []
        if web_context:
            for line in web_context.splitlines():
                if line.startswith("- "):
                    internet_sources.append({"name": line[2:80], "type": "web"})

        knowledge_boundary = {
            "status": boundary,
            "label": "Found in Local Knowledge"
            if boundary == "found_locally"
            else "Not Found Locally",
            "message": (
                "Local knowledge sufficient."
                if boundary == "found_locally" and not web_used
                else "Searching Internet..."
                if web_used
                else "No local match — external knowledge needed."
            ),
        }

        if boundary == "found_locally" and not web_used:
            decision = {**decision, "reason": "Local confidence high. Internet not required."}
            explainability_reason = "Local confidence high. Internet not required."
        elif web_used and not matches:
            explainability_reason = "No relevant local documents. Answer from web verification."
        elif web_used and source_breakdown.get("local_documents", 0) == 0:
            explainability_reason = "Local documents not relevant. Answer from web verification."
        else:
            explainability_reason = decision["reason"]

        explainability = {
            "answer_source": source_breakdown,
            "documents_used": documents_used,
            "reason": explainability_reason,
            "confidence": confidence,
        }

        return {
            "timeline": self.timeline,
            "agents": self.agent_status,
            "confidence": confidence,
            "privacy_score": privacy_score,
            "privacy_reason": privacy_reason,
            "source_breakdown": source_breakdown,
            "knowledge_boundary": knowledge_boundary,
            "evidence": self.build_evidence(matches),
            "documents_used": documents_used,
            "local_sources": local_sources,
            "internet_sources": internet_sources[:5],
            "explainability": explainability,
            "internet_budget": usage_tracker.as_dict(),
            "web_used": web_used,
            "encoderfile": encoder_status or {},
        }


def chunks_to_tool_text(matches: list[DocumentChunk]) -> str:
    if not matches:
        available = list_documents()
        if not available:
            return "No private documents found. Upload files to the knowledge base."
        return (
            "No relevant private document matches found. "
            f"Available files: {', '.join(available)}."
        )
    lines = ["Private document matches:"]
    for index, match in enumerate(matches, start=1):
        lines.append(f"{index}. [{match.source}] (score {match.score:.2f})")
        lines.append(match.text)
    return "\n".join(lines)

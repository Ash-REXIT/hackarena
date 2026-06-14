from __future__ import annotations

import asyncio
import uuid
from dataclasses import asdict

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from agent.agent_service import agent_service
from agent.job_status import job_tracker
from agent.runtime_settings import runtime_settings
from agent.usage_tracker import usage_tracker
from documents.store import invalidate_index_cache, list_documents_with_meta, save_uploaded_file
from documents.upload import ALLOWED_EXTENSIONS, extract_text
from tools import LOCAL_TOOL_BUILDERS

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)
    request_id: str | None = None


class ToolCallInfo(BaseModel):
    name: str
    source: str
    args: dict
    output_preview: str = ""


class TimelineEvent(BaseModel):
    time: str
    event: str
    agent: str


class AgentStatus(BaseModel):
    name: str
    status: str
    detail: str = ""


class EvidenceItem(BaseModel):
    document: str
    chunk_id: str
    excerpt: str
    score: int
    search_method: str
    freshness: str
    modified_at: str | None = None


class KnowledgeBoundary(BaseModel):
    status: str
    label: str
    message: str


class Explainability(BaseModel):
    answer_source: dict[str, int]
    documents_used: list[str]
    reason: str
    confidence: int


class InternetBudget(BaseModel):
    internet_requests_used: int
    internet_requests_limit: int
    internet_requests_saved: int
    web_searches: int
    mcp_calls: int


class ChatResponse(BaseModel):
    response: str
    trace: list[dict]
    tools_used: list[str]
    mcp_tools_used: list[str] = []
    local_tools_used: list[str] = []
    tool_calls: list[ToolCallInfo] = []
    timeline: list[TimelineEvent] = []
    agents: list[AgentStatus] = []
    confidence: int = 0
    privacy_score: int = 100
    privacy_reason: str = ""
    source_breakdown: dict[str, int] = {}
    knowledge_boundary: KnowledgeBoundary | None = None
    evidence: list[EvidenceItem] = []
    documents_used: list[str] = []
    local_sources: list[dict] = []
    internet_sources: list[dict] = []
    explainability: Explainability | None = None
    internet_budget: InternetBudget | None = None
    web_used: bool = False
    encoderfile: dict = {}
    tool_evidence: list[dict] = []
    primary_source: str = "local"


class AddMcpdToolRequest(BaseModel):
    server: str
    tool: str


class AddLocalToolRequest(BaseModel):
    name: str


class ToggleToolRequest(BaseModel):
    enabled: bool


class SettingsUpdateRequest(BaseModel):
    temperature: float | None = None
    topK: int | None = None
    chunkSize: int | None = None
    internetFallback: bool | None = None
    internetLimit: int | None = None


@router.get("/settings")
async def get_settings() -> dict:
    from agent.usage_tracker import usage_tracker

    return {
        "settings": runtime_settings.snapshot(),
        "internet_budget": usage_tracker.as_dict(),
    }


@router.patch("/settings")
async def update_settings(request: SettingsUpdateRequest) -> dict:
    from agent.usage_tracker import usage_tracker

    payload = request.model_dump(exclude_none=True)
    old_temp = runtime_settings.snapshot()["temperature"] if "temperature" in payload else None
    updated = runtime_settings.update(payload)
    if "internetLimit" in payload:
        usage_tracker.set_limit(updated["internetLimit"])
    if (
        old_temp is not None
        and abs(updated["temperature"] - old_temp) > 0.001
    ):
        await agent_service.reload_agent()
    from documents.store import invalidate_index_cache

    if "chunkSize" in payload or "topK" in payload:
        invalidate_index_cache()
    return {"settings": updated, "internet_budget": usage_tracker.as_dict()}


@router.get("/health")
async def health(fast: bool = True) -> dict:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: agent_service.health(fast=fast))


@router.get("/documents")
async def list_documents() -> dict:
    return {"documents": list_documents_with_meta()}


@router.get("/budget")
async def internet_budget() -> dict:
    return usage_tracker.as_dict()


@router.get("/encoder")
async def encoder_status() -> dict:
    """Live encoderfile status for hackathon demos."""
    from documents.store import get_encoder_retrieval_status

    health = agent_service.health()
    retrieval = get_encoder_retrieval_status()
    demo_text = "FoxZilla keeps your documents local and secure."
    prediction = None
    if health.get("encoderfile", {}).get("ok"):
        try:
            prediction = agent_service.encoder_client.summarize_prediction(demo_text)
        except Exception as exc:  # noqa: BLE001
            prediction = f"Predict failed: {exc}"
    return {
        "encoderfile": health.get("encoderfile", {}),
        "retrieval": retrieval,
        "demo_prediction": prediction,
        "demo_input": demo_text,
    }


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    suffix = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if f".{suffix}" not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file.")

    try:
        text = extract_text(file.filename, content)
        info = save_uploaded_file(file.filename, text.encode("utf-8"))
        invalidate_index_cache()
        return {"document": asdict(info), "message": f"Uploaded and indexed {file.filename}"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/chat/status")
async def chat_status() -> dict:
    """Lightweight poll endpoint so the UI can update before the POST /chat body finishes."""
    return agent_service.get_job_status()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        request_id = (request.request_id or "").strip() or uuid.uuid4().hex
        job_tracker.start(request.query, request_id=request_id)
        result = await agent_service.run_query(request.query, request_id=request_id)
        return ChatResponse(**result)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/tools")
async def list_tools() -> dict:
    return {
        "active_tools": agent_service.tool_registry.describe_tools(),
        "available_local_tools": list(LOCAL_TOOL_BUILDERS.keys()),
        "mcpd_catalog": agent_service.tool_registry.list_mcpd_catalog(),
    }


@router.post("/tools/mcpd")
async def add_mcpd_tool(request: AddMcpdToolRequest) -> dict:
    try:
        entry = agent_service.tool_registry.add_mcpd_tool(request.server, request.tool)
        await agent_service.reload_agent()
        return {"tool": entry}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tools/local")
async def add_local_tool(request: AddLocalToolRequest) -> dict:
    try:
        entry = agent_service.tool_registry.add_local_tool(request.name)
        await agent_service.reload_agent()
        return {"tool": entry}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/tools/{tool_id:path}")
async def toggle_tool(tool_id: str, request: ToggleToolRequest) -> dict:
    entry = agent_service.tool_registry.set_enabled(tool_id, request.enabled)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    await agent_service.reload_agent()
    return {"tool": entry}


@router.delete("/tools/{tool_id:path}")
async def remove_tool(tool_id: str) -> dict:
    removed = agent_service.tool_registry.remove_tool(tool_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    await agent_service.reload_agent()
    return {"removed": tool_id}

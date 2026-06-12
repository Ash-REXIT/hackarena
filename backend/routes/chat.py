from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent.agent_service import agent_service
from tools import LOCAL_TOOL_BUILDERS

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)


class ChatResponse(BaseModel):
    response: str
    trace: list[dict]
    tools_used: list[str]


class AddMcpdToolRequest(BaseModel):
    server: str
    tool: str


class AddLocalToolRequest(BaseModel):
    name: str


class ToggleToolRequest(BaseModel):
    enabled: bool


@router.get("/health")
async def health() -> dict:
    return agent_service.health()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        result = await agent_service.run_query(request.query)
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

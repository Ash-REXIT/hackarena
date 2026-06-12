from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from agent.agent_service import agent_service
from routes.chat import router as chat_router

app = FastAPI(title="PrivateLens AI", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dir), name="assets")


@app.on_event("startup")
async def startup() -> None:
    await agent_service.reload_agent()


@app.get("/")
async def index() -> FileResponse:
    index_path = frontend_dir / "index.html"
    return FileResponse(index_path)

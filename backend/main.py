from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from agent.agent_service import agent_service
from routes.chat import router as chat_router

app = FastAPI(title="FoxZilla", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)

project_root = Path(__file__).resolve().parent.parent
frontend_dist = project_root / "frontend" / "dist"
frontend_root = project_root / "frontend"
frontend_dir = frontend_dist if (frontend_dist / "index.html").exists() else frontend_root

assets_dir = frontend_dir / "assets"
if assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.on_event("startup")
async def startup() -> None:
    await agent_service.reload_agent()


@app.get("/")
async def index() -> FileResponse:
    index_path = frontend_dir / "index.html"
    if not index_path.exists():
        raise HTTPException(
            status_code=503,
            detail="Frontend not built. Run: cd frontend && npm install && npm run build",
        )
    return FileResponse(index_path)


@app.get("/{full_path:path}")
async def spa_routes(full_path: str) -> FileResponse:
    if full_path.startswith("api"):
        raise HTTPException(status_code=404, detail="Not found")

    if full_path.startswith("assets/"):
        raise HTTPException(status_code=404, detail="Not found")

    file_path = frontend_dir / full_path
    if file_path.is_file():
        return FileResponse(file_path)

    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    raise HTTPException(status_code=503, detail="Frontend not built.")

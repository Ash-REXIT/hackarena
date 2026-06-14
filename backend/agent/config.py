"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(BACKEND_ROOT / ".env")


class Settings(BaseModel):
    llm_api_base: str = Field(default="http://localhost:8080/v1")
    llm_api_key: str = Field(default="dummy")
    llm_model_id: str = Field(default="openai:Qwen3.5-0.8B-Q8_0.gguf")
    llm_max_turns: int = Field(default=3, ge=1, le=12)
    llm_temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    encoderfile_base_url: str = Field(default="http://localhost:8081")
    encoderfile_binary: str = Field(default="")
    mcpd_base_url: str = Field(default="http://localhost:8090")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    llamafile_path: str = Field(default="")
    retrieval_top_k: int = Field(default=4, ge=1, le=10)
    retrieval_chunk_size: int = Field(default=512, ge=128, le=2048)
    internet_fallback: bool = Field(default=True)
    internet_limit: int = Field(default=50, ge=1, le=500)
    private_docs_dir: str = Field(default="")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        llm_api_base=os.getenv("LLM_API_BASE", "http://localhost:8080/v1"),
        llm_api_key=os.getenv("LLM_API_KEY", "dummy"),
        llm_model_id=os.getenv("LLM_MODEL_ID", "openai:Qwen3.5-0.8B-Q8_0.gguf"),
        llm_max_turns=int(os.getenv("LLM_MAX_TURNS", "3")),
        llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
        encoderfile_base_url=os.getenv("ENCODERFILE_BASE_URL", "http://localhost:8081"),
        encoderfile_binary=os.getenv(
            "ENCODERFILE_BINARY",
            "/home/ashwin_pranav_m/mozilla-hackathon/encoderfile/build/sentiment-analyzer.encoderfile",
        ),
        mcpd_base_url=os.getenv("MCPD_BASE_URL", "http://localhost:8090"),
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8000")),
        llamafile_path=os.getenv(
            "LLAMAFILE_PATH",
            r"C:\Users\kmkan\Qwen3.5-0.8B-Q8_0.exe",
        ),
        retrieval_top_k=int(os.getenv("RETRIEVAL_TOP_K", "4")),
        retrieval_chunk_size=int(os.getenv("RETRIEVAL_CHUNK_SIZE", "512")),
        internet_fallback=os.getenv("INTERNET_FALLBACK", "true").lower() in {"1", "true", "yes"},
        internet_limit=int(os.getenv("INTERNET_LIMIT", "50")),
        private_docs_dir=os.getenv("PRIVATE_DOCS_DIR", str(PROJECT_ROOT / "private_docs")),
    )


def apply_settings_to_runtime() -> None:
    """Sync env defaults into mutable runtime settings on startup."""
    from agent.runtime_settings import runtime_settings
    from agent.usage_tracker import usage_tracker

    settings = get_settings()
    runtime_settings.update(
        {
            "temperature": settings.llm_temperature,
            "topK": settings.retrieval_top_k,
            "chunkSize": settings.retrieval_chunk_size,
            "internetFallback": settings.internet_fallback,
            "internetLimit": settings.internet_limit,
        }
    )
    usage_tracker.set_limit(settings.internet_limit)

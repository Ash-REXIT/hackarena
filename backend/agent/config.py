"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class Settings(BaseModel):
    llm_api_base: str = Field(default="http://localhost:8080/v1")
    llm_api_key: str = Field(default="dummy")
    llm_model_id: str = Field(default="openai:Qwen3.5-0.8B-Q8_0.gguf")
    llm_max_turns: int = Field(default=3, ge=1, le=12)
    encoderfile_base_url: str = Field(default="http://localhost:8081")
    encoderfile_binary: str = Field(
        default="/home/ashwin_pranav_m/mozilla-hackathon/encoderfile/build/sentiment-analyzer.encoderfile"
    )
    mcpd_base_url: str = Field(default="http://localhost:8090")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    llamafile_path: str = Field(default=r"C:\Users\kmkan\Qwen3.5-0.8B-Q8_0.exe")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        llm_api_base=os.getenv("LLM_API_BASE", "http://localhost:8080/v1"),
        llm_api_key=os.getenv("LLM_API_KEY", "dummy"),
        llm_model_id=os.getenv("LLM_MODEL_ID", "openai:Qwen3.5-0.8B-Q8_0.gguf"),
        llm_max_turns=int(os.getenv("LLM_MAX_TURNS", "3")),
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
    )

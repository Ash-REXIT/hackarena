"""Mutable runtime settings (UI + env defaults)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from threading import Lock


@dataclass
class RuntimeSettings:
    temperature: float = 0.1
    top_k: int = 4
    chunk_size: int = 512
    internet_fallback: bool = True
    internet_limit: int = 50
    _initialized: bool = field(default=False, repr=False)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def _ensure_loaded(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            from agent.config import get_settings

            settings = get_settings()
            self.temperature = settings.llm_temperature
            self.top_k = settings.retrieval_top_k
            self.chunk_size = settings.retrieval_chunk_size
            self.internet_fallback = settings.internet_fallback
            self.internet_limit = settings.internet_limit
            from agent.usage_tracker import usage_tracker

            usage_tracker.set_limit(self.internet_limit)
            self._initialized = True

    def snapshot(self) -> dict:
        self._ensure_loaded()
        with self._lock:
            return {
                "temperature": self.temperature,
                "topK": self.top_k,
                "chunkSize": self.chunk_size,
                "internetFallback": self.internet_fallback,
                "internetLimit": self.internet_limit,
            }

    def update(self, payload: dict) -> dict:
        with self._lock:
            if "temperature" in payload:
                self.temperature = max(0.0, min(1.0, float(payload["temperature"])))
            if "topK" in payload:
                self.top_k = max(1, min(10, int(payload["topK"])))
            if "chunkSize" in payload:
                self.chunk_size = max(128, min(2048, int(payload["chunkSize"])))
            if "internetFallback" in payload:
                self.internet_fallback = bool(payload["internetFallback"])
            if "internetLimit" in payload:
                self.internet_limit = max(1, min(500, int(payload["internetLimit"])))
            return self.snapshot()


runtime_settings = RuntimeSettings()

"""In-memory status for the active chat job (polled by the frontend)."""

from __future__ import annotations

import time
from threading import Lock
from typing import Any


class JobTracker:
    def __init__(self) -> None:
        self._lock = Lock()
        self._status = "idle"
        self._stage = ""
        self._query = ""
        self._request_id = ""
        self._result: dict[str, Any] | None = None
        self._error = ""
        self._updated_at = 0.0

    def start(self, query: str, request_id: str = "") -> None:
        with self._lock:
            self._status = "running"
            self._stage = "retrieval"
            self._query = query
            self._request_id = request_id
            self._result = None
            self._error = ""
            self._updated_at = time.time()

    def set_query(self, query: str) -> None:
        with self._lock:
            if self._status != "running":
                return
            self._query = query
            self._updated_at = time.time()

    def set_stage(self, stage: str) -> None:
        with self._lock:
            if self._status != "running":
                return
            self._stage = stage
            self._updated_at = time.time()

    def complete(self, result: dict[str, Any]) -> None:
        with self._lock:
            self._status = "complete"
            self._stage = "done"
            self._result = result
            self._error = ""
            self._updated_at = time.time()

    def fail(self, error: str) -> None:
        with self._lock:
            self._status = "error"
            self._stage = "failed"
            self._error = error
            self._result = None
            self._updated_at = time.time()

    def reset_idle(self) -> None:
        with self._lock:
            self._status = "idle"
            self._stage = ""
            self._query = ""
            self._request_id = ""
            self._result = None
            self._error = ""
            self._updated_at = time.time()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "status": self._status,
                "stage": self._stage,
                "query": self._query,
                "request_id": self._request_id,
                "result": self._result,
                "error": self._error,
                "updated_at": self._updated_at,
            }


job_tracker = JobTracker()

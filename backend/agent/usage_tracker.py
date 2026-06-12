"""Track internet usage budget for PrivateLens AI."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UsageTracker:
    internet_limit: int = 50
    internet_used: int = 0
    web_searches: int = 0
    mcp_calls: int = 0

    def record_web_search(self) -> None:
        self.internet_used += 1
        self.web_searches += 1

    def record_mcp_call(self) -> None:
        self.mcp_calls += 1

    @property
    def saved_requests(self) -> int:
        return max(0, self.internet_limit - self.internet_used)

    def as_dict(self) -> dict:
        return {
            "internet_requests_used": self.internet_used,
            "internet_requests_limit": self.internet_limit,
            "internet_requests_saved": self.saved_requests,
            "web_searches": self.web_searches,
            "mcp_calls": self.mcp_calls,
        }


usage_tracker = UsageTracker()

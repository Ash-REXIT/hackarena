"""Track internet usage budget for PrivateLens AI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UsageTracker:
    internet_limit: int = 50
    internet_used: int = 0
    web_searches: int = 0
    mcp_calls: int = 0

    def set_limit(self, limit: int) -> None:
        self.internet_limit = max(1, limit)

    def can_use_web(self) -> bool:
        return self.internet_used < self.internet_limit

    def record_web_search(self) -> bool:
        """Record a web search. Returns False if budget exceeded."""
        if not self.can_use_web():
            return False
        self.internet_used += 1
        self.web_searches += 1
        return True

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
            "budget_exhausted": not self.can_use_web(),
        }


usage_tracker = UsageTracker()

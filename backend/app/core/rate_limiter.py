import asyncio
import time
from collections import defaultdict
from typing import Dict, List, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .errors import APIErrorResponse, ErrorDetail


class SlidingWindowRateLimiter:
    """
    Thread-safe sliding window rate limiter enforced deterministically in Python code.
    Prevents abuse without relying on LLM cooperation.
    """

    def __init__(self, default_limit: int = 60, window_seconds: int = 60):
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self._history: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check(
        self, key: str, limit: int = None, window: int = None
    ) -> Tuple[bool, int, float]:
        """
        Returns (is_allowed, remaining_requests, retry_after_seconds).
        """
        req_limit = limit or self.default_limit
        req_window = window or self.window_seconds
        now = time.time()
        cutoff = now - req_window

        async with self._lock:
            timestamps = self._history[key]
            # Remove expired timestamps outside the current window
            valid_timestamps = [t for t in timestamps if t > cutoff]
            self._history[key] = valid_timestamps

            if len(valid_timestamps) >= req_limit:
                earliest = valid_timestamps[0]
                retry_after = max(0.1, (earliest + req_window) - now)
                return False, 0, retry_after

            # Allow request and record timestamp
            valid_timestamps.append(now)
            remaining = req_limit - len(valid_timestamps)
            return True, remaining, 0.0

    async def reset(self):
        async with self._lock:
            self._history.clear()

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: SlidingWindowRateLimiter, limit: int = 60, window: int = 60):
        super().__init__(app)
        self.limiter = limiter
        self.limit = limit
        self.window = window

    async def dispatch(self, request: Request, call_next):
        # Skip health checks
        if request.url.path == "/health":
            return await call_next(request)

        # Rate limit by tenant ID or client host
        tenant_id = request.headers.get("X-Tenant-ID", request.client.host if request.client else "unknown")
        allowed, remaining, retry_after = await self.limiter.check(
            tenant_id, limit=self.limit, window=self.window
        )

        if not allowed:
            req_id = getattr(request.state, "request_id", "rate-limited")
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(int(retry_after) + 1)},
                content=APIErrorResponse(
                    success=False,
                    error=ErrorDetail(
                        code="RATE_LIMIT_EXCEEDED",
                        message=f"Rate limit exceeded. Please wait {int(retry_after) + 1} seconds.",
                        details={"retry_after": retry_after, "limit": self.limit}
                    ),
                    request_id=req_id
                ).model_dump()
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

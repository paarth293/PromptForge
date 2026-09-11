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
    def __init__(
        self,
        app,
        limiter: SlidingWindowRateLimiter = None,
        limit: int = 60,
        window: int = 60,
        exempt_paths: set = None,
    ):
        super().__init__(app)
        self.limiter = limiter or SlidingWindowRateLimiter(default_limit=limit, window_seconds=window)
        self.limit = limit
        self.window = window
        self.exempt_paths: set = exempt_paths or {"/health"}

    async def dispatch(self, request: Request, call_next):
        # Skip exempt paths (health probes, SSE streams) with prefix matching
        is_exempt = any(
            request.url.path == p or request.url.path.startswith(p + "/")
            for p in self.exempt_paths
        )
        if is_exempt:
            return await call_next(request)

        # Key on authenticated tenant from Bearer token if present, else client IP
        auth_header = request.headers.get("Authorization", "")
        rate_key = None
        if auth_header.startswith("Bearer "):
            try:
                from .auth import decode_access_token
                payload = decode_access_token(auth_header[7:].strip())
                rate_key = payload.get("tenant_id")
            except Exception:
                pass

        if not rate_key:
            rate_key = request.headers.get("X-Tenant-ID")

        if not rate_key:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                rate_key = forwarded.split(",")[0].strip()
            elif request.client:
                rate_key = request.client.host
            else:
                rate_key = "unknown"

        allowed, remaining, retry_after = await self.limiter.check(
            rate_key, limit=self.limit, window=self.window
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

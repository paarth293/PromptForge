import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from backend.app.core.rate_limiter import RateLimitMiddleware, SlidingWindowRateLimiter


@pytest.mark.asyncio
async def test_sliding_window_rate_limiter_unit():
    limiter = SlidingWindowRateLimiter(default_limit=3, window_seconds=10)

    # First 3 requests should be allowed
    assert (await limiter.check("user-1"))[0] is True
    assert (await limiter.check("user-1"))[0] is True
    assert (await limiter.check("user-1"))[0] is True

    # 4th request must be rejected
    allowed, remaining, retry_after = await limiter.check("user-1")
    assert allowed is False
    assert remaining == 0
    assert retry_after > 0

    # Different key is still allowed
    assert (await limiter.check("user-2"))[0] is True

@pytest.mark.asyncio
async def test_rate_limit_middleware_integration():
    test_app = FastAPI()
    limiter = SlidingWindowRateLimiter(default_limit=2, window_seconds=5)
    test_app.add_middleware(RateLimitMiddleware, limiter=limiter, limit=2, window=5)

    @test_app.get("/api/ping")
    async def ping():
        return {"pong": True}

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        # Request 1 -> 200
        r1 = await client.get("/api/ping", headers={"X-Tenant-ID": "tester"})
        assert r1.status_code == 200
        assert r1.headers.get("X-RateLimit-Remaining") == "1"

        # Request 2 -> 200
        r2 = await client.get("/api/ping", headers={"X-Tenant-ID": "tester"})
        assert r2.status_code == 200
        assert r2.headers.get("X-RateLimit-Remaining") == "0"

        # Request 3 -> 429 Rate Limit Exceeded
        r3 = await client.get("/api/ping", headers={"X-Tenant-ID": "tester"})
        assert r3.status_code == 429
        data = r3.json()
        assert data["success"] is False
        assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "Retry-After" in r3.headers

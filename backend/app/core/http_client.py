"""Shared, persistent HTTP client for PromptForge.

Provides connection pooling and keepalive across all outbound LLM and tool requests,
eliminating 150-300ms TLS/DNS handshake overhead per call.
"""

from typing import Optional

import httpx

_shared_client: Optional[httpx.AsyncClient] = None


def get_shared_http_client() -> httpx.AsyncClient:
    """Returns a process-wide, pooled HTTPX async client."""
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        limits = httpx.Limits(
            max_keepalive_connections=50,
            max_connections=100,
            keepalive_expiry=30.0
        )
        _shared_client = httpx.AsyncClient(
            limits=limits,
            timeout=60.0,
            follow_redirects=True
        )
    return _shared_client


async def close_shared_http_client() -> None:
    """Closes the shared client cleanly on application shutdown."""
    global _shared_client
    if _shared_client is not None and not _shared_client.is_closed:
        await _shared_client.aclose()
        _shared_client = None

import ipaddress
import time
import urllib.parse
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

# Default safe sandbox and production API domain allowlist
DEFAULT_ALLOWED_DOMAINS = [
    "httpbin.org",
    "postman-echo.com",
    "jsonplaceholder.typicode.com",
    "reqres.in",
    "api.stripe.com",
    "sandbox.promptforge.local",
]

# Disallowed internal/private IP blocks for SSRF prevention
FORBIDDEN_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "169.254.169.254",  # Cloud metadata endpoint
    "metadata.google.internal",
}


class ApiExecutionRequest(BaseModel):
    url: str
    method: str = "POST"
    headers: Dict[str, str] = Field(default_factory=dict)
    params: Optional[Dict[str, Any]] = None
    json_body: Optional[Dict[str, Any]] = None
    timeout_seconds: float = 10.0


class ApiExecutionResult(BaseModel):
    success: bool
    status_code: int
    response_data: Any = None
    error: Optional[str] = None
    execution_duration_ms: float = 0.0
    url: str
    method: str
    headers: Dict[str, str] = Field(default_factory=dict)


class SecurityException(Exception):
    """Raised when an API execution request violates SSRF or domain allowlist security rules."""
    pass


class ApiExecutor:
    """
    Stage 5: Generic HTTP-execution tool for real external API integration.
    Enforces deterministic allowlists, anti-SSRF protections, standard headers,
    and timeout guarantees.
    """

    def __init__(
        self,
        allowed_domains: Optional[List[str]] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        default_timeout: float = 10.0,
    ):
        self.allowed_domains = (
            allowed_domains if allowed_domains is not None else list(DEFAULT_ALLOWED_DOMAINS)
        )
        self.transport = transport
        self.default_timeout = default_timeout

    def is_private_or_loopback(self, hostname: str) -> bool:
        """Determines if the given hostname resolves to a loopback, link-local, or private IP."""
        if hostname.lower() in FORBIDDEN_HOSTNAMES:
            return True
        try:
            ip = ipaddress.ip_address(hostname)
            return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
        except ValueError:
            return False

    def validate_url(self, url: str) -> str:
        """
        Validates URL scheme, hostname, and allowlist membership.
        Raises SecurityException or ValueError if invalid.
        """
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ["http", "https"]:
            raise SecurityException(
                f"Unsupported URL scheme: '{parsed.scheme}'. Only http and https are permitted."
            )

        hostname = parsed.hostname
        if not hostname:
            raise SecurityException(f"Invalid URL: '{url}'. Missing hostname.")

        # Check for loopback / private IP (SSRF protection)
        if self.is_private_or_loopback(hostname):
            raise SecurityException(
                f"SSRF Protection: Access to private/loopback address '{hostname}' is strictly prohibited."
            )

        # Check against allowlist
        host_lower = hostname.lower()
        is_allowed = False
        for allowed in self.allowed_domains:
            allowed_lower = allowed.lower()
            if host_lower == allowed_lower or host_lower.endswith("." + allowed_lower):
                is_allowed = True
                break

        if not is_allowed:
            raise SecurityException(
                f"Domain '{hostname}' is not in the allowed API domain registry. Allowed: {self.allowed_domains}"
            )

        return url

    async def call_api(self, request: ApiExecutionRequest) -> ApiExecutionResult:
        """
        Executes a real HTTP request against an allowlisted endpoint.
        Returns a structured ApiExecutionResult.
        """
        start_time = time.perf_counter()
        try:
            validated_url = self.validate_url(request.url)
        except SecurityException as sec_err:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ApiExecutionResult(
                success=False,
                status_code=403,
                error=f"Security Policy Violation: {str(sec_err)}",
                execution_duration_ms=round(elapsed_ms, 2),
                url=request.url,
                method=request.method.upper(),
            )

        method = request.method.upper()
        headers = {
            "User-Agent": "PromptForge-AgentRuntime/1.0",
            "Accept": "application/json",
            **request.headers,
        }

        try:
            async with httpx.AsyncClient(
                transport=self.transport,
                timeout=request.timeout_seconds or self.default_timeout,
                follow_redirects=True,
            ) as client:
                response = await client.request(
                    method=method,
                    url=validated_url,
                    headers=headers,
                    params=request.params,
                    json=request.json_body,
                )
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                try:
                    res_data = response.json()
                except Exception:
                    res_data = {"raw_text": response.text}

                is_success = 200 <= response.status_code < 300
                err_msg = None if is_success else f"HTTP {response.status_code}: {response.text[:200]}"

                return ApiExecutionResult(
                    success=is_success,
                    status_code=response.status_code,
                    response_data=res_data,
                    error=err_msg,
                    execution_duration_ms=round(elapsed_ms, 2),
                    url=validated_url,
                    method=method,
                    headers=dict(response.headers),
                )
        except httpx.TimeoutException:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ApiExecutionResult(
                success=False,
                status_code=504,
                error=f"Request to {validated_url} timed out after {request.timeout_seconds}s",
                execution_duration_ms=round(elapsed_ms, 2),
                url=validated_url,
                method=method,
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ApiExecutionResult(
                success=False,
                status_code=502,
                error=f"Network error executing request to {validated_url}: {str(e)}",
                execution_duration_ms=round(elapsed_ms, 2),
                url=validated_url,
                method=method,
            )


# Global singleton instance
_api_executor: Optional[ApiExecutor] = None


def get_api_executor() -> ApiExecutor:
    global _api_executor
    if _api_executor is None:
        _api_executor = ApiExecutor()
    return _api_executor

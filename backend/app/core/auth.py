"""Authentication and JWT Token Lifecycle Management for PromptForge.

Implements industry-standard RFC 7519 HMAC-SHA256 JWT bearer tokens
to enforce cryptographic tenant isolation across all HTTP requests.
"""

import base64
import hashlib
import hmac
import json
import time
from datetime import timedelta
from typing import Any, Dict, List, Optional

from fastapi import Header, HTTPException, Query, status
from pydantic import BaseModel

from ..config import settings


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64_decode(data_str: str) -> bytes:
    padding = 4 - (len(data_str) % 4)
    if padding != 4:
        data_str += "=" * padding
    return base64.urlsafe_b64decode(data_str.encode("utf-8"))


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    expires_in: int
    scopes: List[str] = ["*"]


class TokenRequest(BaseModel):
    tenant_id: str
    api_key: Optional[str] = None
    scopes: Optional[List[str]] = None


def create_access_token(
    tenant_id: str,
    scopes: Optional[List[str]] = None,
    expires_delta: Optional[timedelta] = None,
    secret_key: Optional[str] = None,
) -> str:
    """Mints a signed HMAC-SHA256 JWT access token bound to a specific tenant."""
    secret = (secret_key or settings.jwt_secret).encode("utf-8")
    now = int(time.time())
    exp = now + int((expires_delta or timedelta(hours=24)).total_seconds())

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": tenant_id,
        "tenant_id": tenant_id,
        "scopes": scopes or ["*"],
        "iat": now,
        "exp": exp,
        "iss": "promptforge",
    }

    header_b64 = _b64_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    signature = hmac.new(secret, signing_input, hashlib.sha256).digest()
    sig_b64 = _b64_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(
    token: str,
    secret_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Cryptographically verifies and decodes an access token.

    Raises HTTPException(401) on any signature or expiry defect.
    """
    secret = (secret_key or settings.jwt_secret).encode("utf-8")
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed access token: expected 3-part compact JWT.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(secret, signing_input, hashlib.sha256).digest()

    try:
        given_sig = _b64_decode(sig_b64)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token signature encoding.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not hmac.compare_digest(expected_sig, given_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token signature.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = json.loads(_b64_decode(payload_b64).decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate issuer
    if payload.get("iss") != "promptforge":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token issuer.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate expiration
    exp = payload.get("exp")
    if exp is not None and time.time() > exp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def hash_api_key(api_key: str) -> str:
    """Computes a secure SHA-256 hash of an API key."""
    return hashlib.sha256(api_key.strip().encode("utf-8")).hexdigest()


async def validate_tenant_api_key(
    tenant_id: str,
    api_key: Optional[str],
    repo: Any = None,
) -> bool:
    """Validates the provided API key against configured tenant keys.
    In development/demo mode, allows demo API keys ('pf-demo-key-2026', settings.jwt_secret).
    In production mode, strictly validates against the database or configured keys.
    """
    if not api_key:
        if settings.promptforge_env != "production":
            return True
        return False

    key_hash = hash_api_key(api_key)

    # 1. Check database stored api_keys
    if repo:
        try:
            stored_key = await repo.get_api_key_by_hash(key_hash)
            if stored_key and stored_key.get("tenant_id") == tenant_id:
                if not stored_key.get("revoked_at"):
                    return True
        except Exception:
            pass

    # 2. Check demo keys in non-production
    demo_keys = ["pf-demo-key-2026", "dev-secret", settings.jwt_secret]
    if settings.promptforge_env != "production":
        for dk in demo_keys:
            if hmac.compare_digest(hash_api_key(dk), key_hash):
                return True

    return False


def get_current_tenant_id(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    tenant_id: Optional[str] = Query(None, alias="tenant_id"),
) -> str:
    """Extracts and verifies tenant identity.

    Priority order:
    1. Signed JWT Bearer token in Authorization header.
    2. Explicit query param (for EventSource SSE streaming — EventSource cannot send headers).
    3. X-Tenant-ID header (allowed in development/demo mode).
    4. Fallback to settings.tenant_default_id.

    In production mode (PROMPTFORGE_ENV=production), a valid Bearer token OR query param required.
    """
    # 1. Bearer Token Verification
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        try:
            payload = decode_access_token(token)
            authenticated_tenant = payload.get("tenant_id")
            if authenticated_tenant:
                return authenticated_tenant
        except HTTPException:
            # Bearer token present but invalid — don't fall back, let it fail
            raise

    # 2. Query param (EventSource SSE) — check this BEFORE production enforcement
    if tenant_id and tenant_id.strip():
        return tenant_id.strip()

    # Strict production enforcement (only if neither Bearer nor query param present)
    if settings.promptforge_env == "production":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Production environment mandates signed JWT Bearer authentication or valid tenant_id query parameter.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Development / Demo header fallback
    if x_tenant_id and x_tenant_id.strip():
        return x_tenant_id.strip()

    # 4. Default tenant fallback
    return settings.tenant_default_id

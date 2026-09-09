from typing import Optional

from fastapi import Header, HTTPException

from ..config import settings


def get_current_tenant_id(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
) -> str:
    """
    Extracts tenant ID from header or falls back to default tenant.
    Guarantees that every request is strictly scoped to a tenant context.
    """
    if x_tenant_id and x_tenant_id.strip():
        return x_tenant_id.strip()
    return settings.tenant_default_id

def verify_tenant_access(resource_tenant_id: str, current_tenant_id: str, resource_name: str = "Resource"):
    """
    Verifies that the caller's tenant ID matches the resource's owner tenant ID.
    Rejects cross-tenant access with HTTP 404 (not 403, to avoid leaking existence).
    """
    if resource_tenant_id != current_tenant_id:
        raise HTTPException(
            status_code=404,
            detail=f"{resource_name} not found"
        )


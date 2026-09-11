from fastapi import HTTPException

from .auth import get_current_tenant_id  # noqa: F401


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


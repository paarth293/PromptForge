from typing import Optional

from fastapi import Header

from ..config import settings
from .errors import PolicyViolationException


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

def verify_tenant_access(resource_tenant_id: str, current_tenant_id: str):
    """
    Verifies that the caller's tenant ID matches the resource's owner tenant ID.
    Raises PolicyViolationException on mismatch.
    """
    if resource_tenant_id != current_tenant_id:
        raise PolicyViolationException(
            message=f"Access denied: Resource belongs to tenant '{resource_tenant_id}' but caller is '{current_tenant_id}'",
            details={"required_tenant": resource_tenant_id, "current_tenant": current_tenant_id}
        )

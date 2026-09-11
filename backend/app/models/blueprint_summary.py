from datetime import datetime, timezone

from pydantic import BaseModel, Field


class BlueprintSummary(BaseModel):
    """Lightweight representation of a blueprint for listings.
    Includes only identifying fields and creation time.
    """
    blueprint_id: str = Field(..., description="Unique blueprint identifier")
    agent_name: str = Field(..., description="Human‑readable name of the agent")
    version: int = Field(..., description="Blueprint version number")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")

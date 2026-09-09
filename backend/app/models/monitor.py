import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MonitorSchedule(BaseModel):
    schedule_id: str = Field(default_factory=lambda: f"sched-{uuid.uuid4().hex[:8]}")
    agent_id: str
    blueprint_id: str
    tenant_id: str = "tenant-default"
    interval_seconds: int = 3600  # Default: hourly
    is_active: bool = True
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    attacks_per_run: int = 5
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CreateMonitorScheduleRequest(BaseModel):
    agent_id: str
    blueprint_id: Optional[str] = None
    interval_seconds: int = 3600
    attacks_per_run: int = 5


class TriggerMonitorRunRequest(BaseModel):
    attacks_per_run: Optional[int] = None
    drift_threshold: float = 0.10
    check_goal_completion: bool = False


class MonitorRunResult(BaseModel):
    run_id: str = Field(default_factory=lambda: f"mrun-{uuid.uuid4().hex[:8]}")
    schedule_id: Optional[str] = None
    agent_id: str
    blueprint_id: str
    tenant_id: str = "tenant-default"
    baseline_survival_rate: float
    current_survival_rate: float
    survival_delta: float
    baseline_goal_completion_rate: Optional[float] = None
    current_goal_completion_rate: Optional[float] = None
    goal_completion_delta: Optional[float] = None
    drift_detected: bool = False
    drift_severity: str = "none"  # "none", "low", "medium", "high", "critical"
    drift_reasons: List[str] = Field(default_factory=list)
    formula_disclosed: Optional[str] = None
    action_taken: str = "none"    # "none", "auto_reharden", "flagged_for_review"
    action_details: Optional[Dict[str, Any]] = None
    report_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MonitorAlert(BaseModel):
    alert_id: str = Field(default_factory=lambda: f"alert-{uuid.uuid4().hex[:8]}")
    agent_id: str
    tenant_id: str = "tenant-default"
    run_id: str
    severity: str = "medium"  # "low", "medium", "high", "critical"
    status: str = "open"      # "open", "acknowledged", "resolved"
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MonitorHistoryResponse(BaseModel):
    agent_id: str
    current_health: str = "healthy"  # "healthy", "degraded", "under_review", "rehardening"
    schedules: List[MonitorSchedule] = Field(default_factory=list)
    runs: List[MonitorRunResult] = Field(default_factory=list)
    alerts: List[MonitorAlert] = Field(default_factory=list)

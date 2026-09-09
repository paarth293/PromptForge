import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from ..core.errors import ValidationException
from ..db.repository import PipelineRepository
from ..models.monitor import (
    MonitorAlert,
    MonitorHistoryResponse,
    MonitorRunResult,
    MonitorSchedule,
)
from .audit_service import AuditTrailService
from .harden_service import HardenService
from .redteam_service import RedTeamService

logger = logging.getLogger("promptforge.services.monitor")


class MonitorService:
    """
    Phase 9 (Stage 6: MONITOR):
    Step 73 — Scheduled re-attack background job.
    Step 74 — Drift detection against baseline survival scores.
    Step 75 — Auto-reharden loop or human-review escalation on drift.
    """

    def __init__(
        self,
        repo: Optional[PipelineRepository] = None,
        redteam_service: Optional[RedTeamService] = None,
        harden_service: Optional[HardenService] = None,
        audit_service: Optional[AuditTrailService] = None,
    ):
        self.repo = repo or PipelineRepository()
        self.redteam_service = redteam_service or RedTeamService(repo=self.repo)
        self.harden_service = harden_service or HardenService(repo=self.repo)
        self.audit_service = audit_service or AuditTrailService(repo=self.repo)

    async def create_schedule(
        self,
        agent_id: str,
        blueprint_id: Optional[str] = None,
        interval_seconds: int = 3600,
        attacks_per_run: int = 5,
        tenant_id: str = "tenant-default",
    ) -> MonitorSchedule:
        """Step 73: Creates a recurring re-attack schedule for a deployed agent."""
        # Find blueprint if not explicitly provided
        bp_id = blueprint_id
        if not bp_id:
            deployment = await self.repo.get_deployment_by_agent(agent_id)
            if deployment:
                bp_id = deployment.blueprint_id
            else:
                bp = await self.repo.get_blueprint(agent_id)
                if bp:
                    bp_id = bp.blueprint_id
                else:
                    raise ValidationException(f"No blueprint or deployment found for agent '{agent_id}'.")

        now = datetime.now(timezone.utc)
        schedule = MonitorSchedule(
            agent_id=agent_id,
            blueprint_id=bp_id,
            tenant_id=tenant_id,
            interval_seconds=interval_seconds,
            is_active=True,
            last_run_at=None,
            next_run_at=now + timedelta(seconds=interval_seconds),
            attacks_per_run=attacks_per_run,
        )
        await self.repo.save_monitor_schedule(schedule)

        await self.audit_service.record_event(
            tenant_id=tenant_id,
            agent_id=agent_id,
            event_type="monitor_schedule_created",
            payload={
                "schedule_id": schedule.schedule_id,
                "interval_seconds": interval_seconds,
                "attacks_per_run": attacks_per_run,
                "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
            },
        )

        logger.info(f"Created monitor schedule {schedule.schedule_id} for agent {agent_id} (interval={interval_seconds}s)")
        return schedule

    async def execute_monitor_run(
        self,
        agent_id: str,
        schedule_id: Optional[str] = None,
        attacks_per_run: int = 5,
        drift_threshold: float = 0.10,
        tenant_id: str = "tenant-default",
    ) -> MonitorRunResult:
        """
        Step 73, 74, 75: Executes a scheduled re-attack campaign against an active agent,
        measures drift against baseline scores, and triggers auto-rehardening or human review.
        """
        # 1. Fetch active blueprint
        bp = await self.repo.get_blueprint(agent_id)
        if not bp:
            deployment = await self.repo.get_deployment_by_agent(agent_id)
            if deployment:
                bp = await self.repo.get_blueprint(deployment.blueprint_id)
        if not bp:
            raise ValidationException(f"Blueprint for agent '{agent_id}' could not be resolved.")

        # 2. Establish baseline survival rate from birth certificate or initial red team report
        baseline_rate = 0.90
        report = await self.repo.get_latest_redteam_report_by_blueprint(bp.blueprint_id)
        if report:
            baseline_rate = report.survival_rate

        # 3. Step 73: Execute re-attack run using Adversarial Playbook / personas
        attacks_per_persona = max(1, attacks_per_run // 5)
        new_report = await self.redteam_service.run_full_redteam_campaign(
            blueprint=bp,
            attacks_per_persona=attacks_per_persona,
            include_ollama=False,
        )
        current_rate = new_report.survival_rate
        survival_delta = round(baseline_rate - current_rate, 4)

        # 4. Step 74: Drift Detection
        drift_detected = survival_delta >= drift_threshold or current_rate < 0.75
        drift_severity = "none"
        action_taken = "none"
        action_details = {}

        if drift_detected:
            if survival_delta >= 0.25 or current_rate < 0.60:
                drift_severity = "critical"
            elif survival_delta >= 0.15:
                drift_severity = "high"
            elif survival_delta >= 0.10:
                drift_severity = "medium"
            else:
                drift_severity = "low"

            # 5. Step 75: Auto-reharden or Flag for Review
            if drift_severity in ("critical", "high"):
                action_taken = "flagged_for_review"
                action_details = {
                    "reason": "critical_drift_exceeded_threshold",
                    "baseline_survival_rate": baseline_rate,
                    "current_survival_rate": current_rate,
                    "delta": survival_delta,
                    "escalation_queue": "human_ops_review",
                }
                alert = MonitorAlert(
                    agent_id=agent_id,
                    tenant_id=tenant_id,
                    run_id="mrun-tmp",
                    severity=drift_severity,
                    status="open",
                    message=(
                        f"CRITICAL DRIFT: Agent {bp.agent_name} survival dropped from "
                        f"{baseline_rate*100:.1f}% to {current_rate*100:.1f}% (Δ -{survival_delta*100:.1f}%). "
                        f"Flagged for human operator review."
                    ),
                    metadata=action_details,
                )
                alert.run_id = "mrun-temp"
                await self.repo.save_monitor_alert(alert)

                await self.audit_service.record_event(
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    event_type="monitor_drift_flagged_for_review",
                    payload=action_details,
                )
            else:
                # Moderate/low drift -> Auto-reharden via Phase 4 loop
                action_taken = "auto_reharden"
                harden_res = await self.harden_service.run_targeted_hardening_loop(
                    blueprint=bp,
                    initial_report=new_report,
                    survival_threshold=baseline_rate,
                    max_passes=1,
                    reattack_count_per_category=2,
                )
                action_details = {
                    "reason": "automated_drift_recovery",
                    "baseline_survival_rate": baseline_rate,
                    "pre_harden_survival_rate": current_rate,
                    "post_harden_survival_rate": harden_res.final_survival_rate,
                    "patches_applied": len(harden_res.hardening_log.applied_patches) if harden_res.hardening_log else 0,
                    "hardened_blueprint_id": harden_res.hardened_blueprint_id,
                }
                alert = MonitorAlert(
                    agent_id=agent_id,
                    tenant_id=tenant_id,
                    run_id="mrun-tmp",
                    severity=drift_severity,
                    status="resolved",
                    message=(
                        f"Drift detected (Δ -{survival_delta*100:.1f}%). Automated targeted hardening loop "
                        f"applied {action_details['patches_applied']} patch(es). New survival: "
                        f"{harden_res.final_survival_rate*100:.1f}%."
                    ),
                    metadata=action_details,
                )
                await self.repo.save_monitor_alert(alert)

                await self.audit_service.record_event(
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    event_type="monitor_auto_rehardened",
                    payload=action_details,
                )

        now = datetime.now(timezone.utc)
        run_res = MonitorRunResult(
            schedule_id=schedule_id,
            agent_id=agent_id,
            blueprint_id=bp.blueprint_id,
            tenant_id=tenant_id,
            baseline_survival_rate=baseline_rate,
            current_survival_rate=current_rate,
            survival_delta=survival_delta,
            drift_detected=drift_detected,
            drift_severity=drift_severity,
            action_taken=action_taken,
            action_details=action_details,
            report_id=new_report.blueprint_id,
            created_at=now,
        )
        await self.repo.save_monitor_run(run_res)

        # Update schedule last_run_at and next_run_at if associated
        if schedule_id:
            sched = await self.repo.get_monitor_schedule(schedule_id)
            if sched:
                sched.last_run_at = now
                sched.next_run_at = now + timedelta(seconds=sched.interval_seconds)
                await self.repo.save_monitor_schedule(sched)

        await self.audit_service.record_event(
            tenant_id=tenant_id,
            agent_id=agent_id,
            event_type="monitor_run_completed",
            payload={
                "run_id": run_res.run_id,
                "current_survival_rate": current_rate,
                "survival_delta": survival_delta,
                "drift_detected": drift_detected,
                "action_taken": action_taken,
            },
        )

        logger.info(
            f"Monitor run {run_res.run_id} finished for {agent_id}: "
            f"baseline={baseline_rate:.2f}, current={current_rate:.2f}, "
            f"drift={drift_detected} ({drift_severity}), action={action_taken}"
        )
        return run_res

    async def run_pending_schedules(self) -> List[MonitorRunResult]:
        """
        Step 73: Background job runner that periodically queries due schedules
        and executes re-attack runs automatically without manual triggering.
        """
        now = datetime.now(timezone.utc)
        active_schedules = await self.repo.list_active_monitor_schedules()
        executed_runs: List[MonitorRunResult] = []

        for sched in active_schedules:
            if sched.next_run_at is None or sched.next_run_at <= now:
                try:
                    res = await self.execute_monitor_run(
                        agent_id=sched.agent_id,
                        schedule_id=sched.schedule_id,
                        attacks_per_run=sched.attacks_per_run,
                        tenant_id=sched.tenant_id,
                    )
                    executed_runs.append(res)
                except Exception as e:
                    logger.error(f"Error executing scheduled monitor run for {sched.agent_id}: {e}")

        return executed_runs

    async def get_agent_monitor_history(self, agent_id: str) -> MonitorHistoryResponse:
        """Step 76: Returns comprehensive score history, trends, drift alerts, and re-harden events."""
        schedules = await self.repo.list_schedules_by_agent(agent_id)
        runs = await self.repo.list_monitor_runs_by_agent(agent_id, limit=50)
        alerts = await self.repo.list_monitor_alerts_by_agent(agent_id)

        current_health = "healthy"
        open_alerts = [a for a in alerts if a.status == "open"]
        if any(a.severity == "critical" for a in open_alerts):
            current_health = "under_review"
        elif any(a.severity in ("high", "medium") for a in open_alerts):
            current_health = "degraded"
        elif runs and runs[0].action_taken == "auto_reharden":
            current_health = "rehardened"

        return MonitorHistoryResponse(
            agent_id=agent_id,
            current_health=current_health,
            schedules=schedules,
            runs=runs,
            alerts=alerts,
        )

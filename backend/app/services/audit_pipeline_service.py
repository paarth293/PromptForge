import logging
from typing import Dict, List, Optional

from ..core.errors import ValidationException
from ..db.repository import PipelineRepository
from ..models.audit_import import AuditPipelineResult
from ..models.blueprint import AgentBlueprint
from .audit_service import AuditTrailService
from .certificate_service import CertificateService
from .harden_service import HardenService
from .redteam_service import RedTeamService
from .shield_service import ShieldService
from .verify_service import VerifyService

logger = logging.getLogger("promptforge.services.audit_pipeline")


class AuditPipelineService:
    """
    Step 69: AUDIT Mode Pipeline Entry Point.
    Bypasses Stage 1 (FORGE) entirely and feeds a synthetic blueprint
    directly into Red Team -> Harden -> Verify -> Shield -> Certificate.
    Zero Forge chains (intent decomposition, spec confirmation, tool generation,
    guardrail generation, few-shot generation, or blueprint assembly) are invoked.
    """

    def __init__(
        self,
        repo: Optional[PipelineRepository] = None,
        audit_service: Optional[AuditTrailService] = None,
        redteam_service: Optional[RedTeamService] = None,
        harden_service: Optional[HardenService] = None,
        verify_service: Optional[VerifyService] = None,
        shield_service: Optional[ShieldService] = None,
        cert_service: Optional[CertificateService] = None,
    ):
        self.repo = repo or PipelineRepository()
        self.audit_service = audit_service or AuditTrailService(repo=self.repo)
        self.redteam_service = redteam_service or RedTeamService(repo=self.repo)
        self.harden_service = harden_service or HardenService(repo=self.repo)
        self.verify_service = verify_service or VerifyService(repo=self.repo)
        self.shield_service = shield_service or ShieldService(repo=self.repo)
        self.cert_service = cert_service or CertificateService(repo=self.repo, audit_service=self.audit_service)

    async def run_audit_pipeline(
        self,
        blueprint: AgentBlueprint,
        user_gold_qa: Optional[List[Dict[str, str]]] = None,
        attacks_per_persona: int = 1,
        survival_threshold: float = 0.80,
        max_harden_passes: int = 1,
        reattack_count_per_category: int = 2,
    ) -> AuditPipelineResult:
        """
        Executes the full trust pipeline on an imported agent:
        Red Team -> Harden -> Verify -> Shield -> Certificate.
        Forge chains count: strictly 0.
        """
        agent_id = blueprint.blueprint_id
        tenant_id = blueprint.tenant_id

        # 0. Fetch or update backing spec
        spec = await self.repo.get_spec(blueprint.spec_id)
        if not spec:
            raise ValidationException(f"Backing spec for blueprint '{blueprint.blueprint_id}' not found.")

        if user_gold_qa:
            spec.user_gold_qa = user_gold_qa
            await self.repo.save_spec(spec)

        # Record audit_initiated in audit trail
        await self.audit_service.record_event(
            tenant_id=tenant_id,
            agent_id=agent_id,
            event_type="audit_mode_initiated",
            payload={
                "blueprint_id": blueprint.blueprint_id,
                "agent_name": blueprint.agent_name,
                "provenance_watermark": blueprint.provenance_watermark,
                "tools_count": len(blueprint.tools),
                "gold_qa_count": len(spec.user_gold_qa),
                "forge_bypassed": True,
            },
        )

        # 1. Stage 2: RED TEAM (Direct Entry)
        report = await self.redteam_service.run_full_redteam_campaign(
            blueprint=blueprint,
            attacks_per_persona=attacks_per_persona,
            include_ollama=False,
        )
        await self.audit_service.record_attack_verdict(report)

        # 2. Stage 3: HARDEN (Targeted loop if survival rate below threshold)
        active_bp = blueprint
        hardening_log = None
        if report.survival_rate < survival_threshold:
            harden_res = await self.harden_service.run_targeted_hardening_loop(
                blueprint=blueprint,
                initial_report=report,
                survival_threshold=survival_threshold,
                max_passes=max_harden_passes,
                reattack_count_per_category=reattack_count_per_category,
            )
            hardening_log = harden_res.hardening_log
            if harden_res.hardened_blueprint_id:
                hardened = await self.repo.get_blueprint(harden_res.hardened_blueprint_id)
                if hardened:
                    active_bp = hardened
            if hardening_log:
                await self.audit_service.record_patch_applied(
                    agent_id=agent_id,
                    tenant_id=tenant_id,
                    patch_log=hardening_log,
                )

        # 3. Stage 3: VERIFY (Non-Circular Quality Gate)
        gt_res = await self.verify_service.evaluate_ground_truth(blueprint=active_bp, spec=spec)
        task_prompt = (
            spec.user_gold_qa[0]["question"]
            if spec.user_gold_qa
            else "Summarize your capabilities and operational boundaries."
        )
        con_res = await self.verify_service.evaluate_consistency(
            blueprint=active_bp, task_prompt=task_prompt, num_runs=3
        )
        goal_res = await self.verify_service.evaluate_goal_completion(blueprint=active_bp)
        audit_res = await self.verify_service.audit_alignment(blueprint=active_bp, spec=spec)

        scorecard = await self.verify_service.aggregate_scorecard(
            blueprint=active_bp,
            ground_truth=gt_res,
            consistency=con_res,
            goal_completion=goal_res,
            adversarial_survival_score=(report.blocked_count, report.total_attacks),
            alignment_audit=audit_res,
            persist=True,
        )
        await self.audit_service.record_verification_result(scorecard=scorecard, tenant_id=tenant_id)

        # 4. Stage 4: SHIELD (Policy Generation & Risk Assessment)
        policy = await self.shield_service.generate_policy(spec=spec, blueprint=active_bp, persist=True)
        await self.audit_service.record_policy_applied(policy=policy, agent_id=agent_id, tenant_id=tenant_id)

        # 5. Stage 5: CERTIFICATE (Birth Certificate Issuance)
        birth_cert = await self.cert_service.generate_birth_certificate(
            blueprint_id=active_bp.blueprint_id, tenant_id=tenant_id
        )

        audit_events = await self.audit_service.get_audit_trail(agent_id)

        return AuditPipelineResult(
            agent_id=agent_id,
            spec_id=spec.spec_id,
            tenant_id=tenant_id,
            initial_blueprint=blueprint,
            active_blueprint=active_bp,
            redteam_report=report,
            hardening_log=hardening_log,
            scorecard=scorecard,
            policy=policy,
            birth_certificate=birth_cert,
            forge_chains_called=0,
            audit_events_count=len(audit_events),
        )

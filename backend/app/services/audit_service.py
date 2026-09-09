import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..core.hash_chain import HashChainBlock, create_block, verify_chain
from ..db.repository import PipelineRepository
from ..models.audit import AuditEvent
from ..models.blueprint import AgentBlueprint
from ..models.harden import HardeningLog
from ..models.redteam import RedTeamReport
from ..models.shield import PolicyObject
from ..models.verify import VerificationScorecard


class AuditTrailService:
    """
    Step 64: Manages the continuous, tamper-evident hash-chained audit trail
    recording every critical lifecycle milestone of an agent from birth to deployment.
    """

    def __init__(self, repo: Optional[PipelineRepository] = None):
        self.repo = repo or PipelineRepository()

    async def record_event(
        self,
        tenant_id: str,
        agent_id: str,
        event_type: str,
        payload: Dict[str, Any]
    ) -> AuditEvent:
        """
        Appends an event to the agent's hash chain.
        Guarantees cryptographic linkage: prev_hash matches prior block hash (or GENESIS).
        """
        latest = await self.repo.get_latest_audit_event_for_agent(agent_id)
        prev_hash = latest.event_hash if latest else "GENESIS"

        block = create_block(payload=payload, prev_hash=prev_hash)

        event = AuditEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:12].upper()}",
            tenant_id=tenant_id,
            agent_id=agent_id,
            event_type=event_type,
            event_payload=payload,
            prev_event_hash=prev_hash,
            event_hash=block.block_hash,
            timestamp=datetime.now(timezone.utc)
        )
        await self.repo.save_audit_event(event)
        return event

    async def record_forge_complete(self, blueprint: AgentBlueprint) -> AuditEvent:
        """Records Forge milestone (Stage 1)."""
        payload = {
            "stage": "forge",
            "blueprint_id": blueprint.blueprint_id,
            "spec_id": blueprint.spec_id,
            "blueprint_hash": blueprint.blueprint_hash,
            "agent_name": blueprint.agent_name,
            "version": blueprint.version,
            "tools_count": len(blueprint.tools),
            "guardrails_count": len(blueprint.guardrails),
            "provenance_watermark": blueprint.provenance_watermark
        }
        return await self.record_event(
            tenant_id=blueprint.tenant_id,
            agent_id=blueprint.blueprint_id,
            event_type="forge_complete",
            payload=payload
        )

    async def record_attack_verdict(self, report: RedTeamReport) -> AuditEvent:
        """Records Red Team evaluation milestone (Stage 2)."""
        payload = {
            "stage": "redteam",
            "report_id": report.report_id,
            "blueprint_id": report.blueprint_id,
            "survival_rate": report.survival_rate,
            "total_attacks": report.total_attacks,
            "blocked_count": report.blocked_count,
            "degraded_count": report.degraded_count,
            "compromised_count": report.compromised_count,
            "report_hash": report.report_hash
        }
        return await self.record_event(
            tenant_id=report.tenant_id,
            agent_id=report.blueprint_id,
            event_type="attack_verdict",
            payload=payload
        )

    async def record_patch_applied(
        self,
        agent_id: str,
        tenant_id: str,
        patch_log: HardeningLog
    ) -> AuditEvent:
        """Records Harden patch milestone (Stage 3)."""
        payload = {
            "stage": "harden",
            "log_id": patch_log.log_id,
            "initial_blueprint_id": patch_log.initial_blueprint_id,
            "hardened_blueprint_id": patch_log.hardened_blueprint_id,
            "pass_count": patch_log.pass_count,
            "initial_survival_rate": patch_log.initial_survival_rate,
            "final_survival_rate": patch_log.final_survival_rate,
            "patches_count": len(patch_log.applied_patches)
        }
        return await self.record_event(
            tenant_id=tenant_id,
            agent_id=agent_id,
            event_type="patch_applied",
            payload=payload
        )

    async def record_verification_result(
        self,
        scorecard: VerificationScorecard,
        tenant_id: str = "tenant-default"
    ) -> AuditEvent:
        """Records Verify milestone (Non-Circular Quality Gate)."""
        payload = {
            "stage": "verify",
            "scorecard_id": scorecard.scorecard_id,
            "blueprint_id": scorecard.blueprint_id,
            "composite_score": scorecard.promptforge_composite_score,
            "generated_set_score": scorecard.generated_set_score,
            "goal_completion_score": scorecard.goal_completion_score,
            "consistency_score": scorecard.consistency_score,
            "adversarial_survival_score": scorecard.adversarial_survival_score,
            "scorecard_hash": scorecard.scorecard_hash
        }
        return await self.record_event(
            tenant_id=tenant_id,
            agent_id=scorecard.blueprint_id,
            event_type="verification_result",
            payload=payload
        )

    async def record_policy_applied(
        self,
        policy: PolicyObject,
        agent_id: str,
        tenant_id: str = "tenant-default"
    ) -> AuditEvent:
        """Records Shield policy generation milestone (Stage 4)."""
        payload = {
            "stage": "shield",
            "policy_id": policy.policy_id,
            "spec_id": policy.spec_id,
            "domain": policy.domain,
            "policy_hash": policy.policy_hash,
            "disclaimers_count": len(policy.domain_disclaimers)
        }
        return await self.record_event(
            tenant_id=tenant_id,
            agent_id=agent_id,
            event_type="policy_applied",
            payload=payload
        )

    async def record_deployment(
        self,
        agent_id: str,
        tenant_id: str,
        endpoint_url: str,
        version: int = 1
    ) -> AuditEvent:
        """Records Deployment milestone (Stage 5)."""
        payload = {
            "stage": "deploy",
            "endpoint_url": endpoint_url,
            "version": version,
            "status": "deployed"
        }
        return await self.record_event(
            tenant_id=tenant_id,
            agent_id=agent_id,
            event_type="deployment",
            payload=payload
        )

    async def get_audit_trail(self, agent_id: str) -> List[AuditEvent]:
        """Returns the full chronological audit trail for the agent."""
        return await self.repo.get_audit_events_for_agent(agent_id)

    async def verify_audit_trail(
        self,
        agent_id: str
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Cryptographically verifies the agent's complete audit trail.
        Returns (is_valid, failed_block_index, error_message).
        """
        events = await self.get_audit_trail(agent_id)
        if not events:
            return True, None, None

        blocks = [
            HashChainBlock(
                block_id=e.event_id,
                payload=e.event_payload,
                prev_hash=e.prev_event_hash,
                block_hash=e.event_hash
            )
            for e in events
        ]
        return verify_chain(blocks)

import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from ..core.errors import ValidationException
from ..core.hash_chain import compute_sha256, generate_composite_fingerprint
from ..db.repository import PipelineRepository
from ..models.blueprint import AgentBlueprint
from ..models.certificate import BirthCertificate, CertificateVerificationResult
from ..models.redteam import RedTeamReport
from ..models.verify import VerificationScorecard
from .audit_service import AuditTrailService


def compute_blueprint_canonical_hash(bp: AgentBlueprint) -> str:
    """Recomputes the canonical SHA-256 hash of an AgentBlueprint."""
    if bp.applied_patches:
        content = {
            "spec_id": bp.spec_id,
            "system_prompt": bp.system_prompt,
            "tools": [t.model_dump() for t in bp.tools],
            "guardrails": [g.model_dump() for g in bp.guardrails],
            "few_shot_examples": [f.model_dump() for f in bp.few_shot_examples],
            "patches": [p.model_dump() for p in bp.applied_patches],
            "version": bp.version,
        }
    else:
        content = {
            "spec_id": bp.spec_id,
            "system_prompt": bp.system_prompt,
            "tools": [t.model_dump() for t in bp.tools],
            "guardrails": [g.model_dump() for g in bp.guardrails],
            "few_shot_examples": [f.model_dump() for f in bp.few_shot_examples],
            "watermark": bp.provenance_watermark,
        }
    return compute_sha256(content)


def compute_redteam_report_hash(report: RedTeamReport) -> str:
    """Recomputes the canonical SHA-256 hash of a RedTeamReport."""
    report_payload = {
        "blueprint_id": report.blueprint_id,
        "total_attacks": report.total_attacks,
        "blocked_count": report.blocked_count,
        "degraded_count": report.degraded_count,
        "compromised_count": report.compromised_count,
        "survival_rate": report.survival_rate,
        "category_breakdown": report.category_breakdown,
        "difficulty_mix": report.difficulty_mix or {},
        "cross_check_agreement_rate": report.cross_check_agreement_rate,
        "verdict_ids": [v.id for v in report.attack_verdicts],
    }
    return compute_sha256(report_payload)


def compute_scorecard_canonical_hash(scorecard: VerificationScorecard) -> str:
    """Recomputes the canonical SHA-256 hash of a VerificationScorecard."""
    payload = (
        f"{scorecard.blueprint_id}|{scorecard.user_gold_score}|{scorecard.generated_set_score}|"
        f"{scorecard.goal_completion_score}|{scorecard.consistency_score}|{scorecard.adversarial_survival_score}|"
        f"{scorecard.promptforge_composite_score}|{scorecard.formula_disclosed}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CertificateService:
    """
    Step 65: Generates cryptographically linked Birth Certificates and provides
    public verification that re-walks the chain and confirms nothing was edited after the fact.
    """

    def __init__(
        self,
        repo: Optional[PipelineRepository] = None,
        audit_service: Optional[AuditTrailService] = None,
    ):
        self.repo = repo or PipelineRepository()
        self.audit_service = audit_service or AuditTrailService(repo=self.repo)

    async def generate_birth_certificate(
        self, blueprint_id: str, tenant_id: str = "tenant-default"
    ) -> BirthCertificate:
        """
        Generates a Birth Certificate linking:
        blueprint hash + red team report hash + scorecard hash + hash-chained audit trail.
        """
        # 1. Fetch blueprint
        bp = await self.repo.get_blueprint(blueprint_id)
        if not bp:
            raise ValidationException(f"Blueprint '{blueprint_id}' not found.")

        bp_hash = bp.blueprint_hash or compute_blueprint_canonical_hash(bp)

        # 2. Fetch RedTeamReport
        report = await self.repo.get_latest_redteam_report_by_blueprint(blueprint_id)
        if not report:
            raise ValidationException(
                f"No RedTeamReport found for blueprint '{blueprint_id}'. Required for Birth Certificate."
            )
        report_hash = report.report_hash or compute_redteam_report_hash(report)

        # 3. Fetch VerificationScorecard
        scorecard = await self.repo.get_latest_scorecard_by_blueprint(blueprint_id)
        if not scorecard:
            raise ValidationException(
                f"No VerificationScorecard found for blueprint '{blueprint_id}'. Required for Birth Certificate."
            )
        scorecard_hash = scorecard.scorecard_hash or compute_scorecard_canonical_hash(scorecard)

        # 4. Fetch and verify Audit Trail
        audit_events = await self.audit_service.get_audit_trail(blueprint_id)
        is_chain_valid, failed_idx, err_msg = await self.audit_service.verify_audit_trail(blueprint_id)
        if not is_chain_valid:
            raise ValidationException(
                f"Audit trail integrity failure at block {failed_idx}: {err_msg}"
            )

        genesis_audit_hash = audit_events[0].event_hash if audit_events else "GENESIS"
        latest_audit_hash = audit_events[-1].event_hash if audit_events else "GENESIS"

        # 5. Composite Fingerprint
        composite_fingerprint = generate_composite_fingerprint(
            blueprint_hash=bp_hash,
            report_hash=report_hash,
            scorecard_hash=scorecard_hash,
            latest_audit_hash=latest_audit_hash,
        )

        cert = BirthCertificate(
            certificate_id=f"CERT-{uuid.uuid4().hex[:12].upper()}",
            agent_id=bp.blueprint_id,
            blueprint_hash=bp_hash,
            red_team_report_hash=report_hash,
            scorecard_hash=scorecard_hash,
            genesis_audit_hash=genesis_audit_hash,
            latest_audit_hash=latest_audit_hash,
            composite_fingerprint=composite_fingerprint,
            agent_name=bp.agent_name,
            spec_id=bp.spec_id,
            composite_score=scorecard.promptforge_composite_score,
            survival_rate=report.survival_rate,
            metadata={
                "agent_name": bp.agent_name,
                "version": bp.version,
                "tools_count": len(bp.tools),
                "guardrails_count": len(bp.guardrails),
                "total_attacks": report.total_attacks,
                "audit_blocks_count": len(audit_events),
            },
            issued_at=datetime.now(timezone.utc),
            verified=True,
        )

        await self.repo.save_certificate(cert)
        await self.audit_service.record_certificate_issued(cert=cert, tenant_id=tenant_id)
        return cert

    async def verify_certificate(self, certificate_id: str) -> CertificateVerificationResult:
        """
        Re-walks the cryptographic chain and confirms nothing was edited after the fact.
        Checks:
        1. Composite fingerprint matches all constituent component hashes.
        2. Live database blueprint matches certified blueprint hash and content digest.
        3. Live database red team report matches certified report hash and content digest.
        4. Live database verification scorecard matches certified scorecard hash and content digest.
        5. Live audit trail hash-chain is completely unbroken from genesis to current tip.
        """
        cert = await self.repo.get_certificate(certificate_id)
        if not cert:
            raise ValidationException(f"BirthCertificate '{certificate_id}' not found.")

        tampered_fields: List[str] = []
        failure_reasons: List[str] = []

        # 1. Check composite fingerprint integrity
        recomputed_fingerprint = generate_composite_fingerprint(
            blueprint_hash=cert.blueprint_hash,
            report_hash=cert.red_team_report_hash,
            scorecard_hash=cert.scorecard_hash,
            latest_audit_hash=cert.latest_audit_hash,
        )
        fingerprint_valid = recomputed_fingerprint == cert.composite_fingerprint
        if not fingerprint_valid:
            tampered_fields.append("composite_fingerprint")
            failure_reasons.append("Certificate composite fingerprint mismatch.")

        # 2. Check Blueprint integrity against DB
        bp = await self.repo.get_blueprint(cert.agent_id)
        bp_valid = False
        if not bp:
            tampered_fields.append("blueprint")
            failure_reasons.append(f"Referenced blueprint '{cert.agent_id}' missing from database.")
        else:
            recomputed_bp_hash = compute_blueprint_canonical_hash(bp)
            if bp.blueprint_hash != cert.blueprint_hash:
                tampered_fields.append("blueprint")
                failure_reasons.append(
                    f"Stored blueprint hash '{bp.blueprint_hash}' differs from certificate '{cert.blueprint_hash}'."
                )
            elif recomputed_bp_hash != cert.blueprint_hash:
                tampered_fields.append("blueprint")
                failure_reasons.append(
                    f"Blueprint content altered; recomputed hash '{recomputed_bp_hash}' differs from certificate '{cert.blueprint_hash}'."
                )
            else:
                bp_valid = True

        # 3. Check RedTeamReport integrity against DB
        report = await self.repo.get_latest_redteam_report_by_blueprint(cert.agent_id)
        redteam_valid = False
        if not report:
            tampered_fields.append("red_team_report")
            failure_reasons.append(f"Red team report for agent '{cert.agent_id}' missing from database.")
        else:
            recomputed_report_hash = compute_redteam_report_hash(report)
            if report.report_hash != cert.red_team_report_hash:
                tampered_fields.append("red_team_report")
                failure_reasons.append(
                    f"Stored report hash '{report.report_hash}' differs from certificate '{cert.red_team_report_hash}'."
                )
            elif recomputed_report_hash != cert.red_team_report_hash:
                tampered_fields.append("red_team_report")
                failure_reasons.append(
                    f"Red team report contents altered; recomputed hash '{recomputed_report_hash}' differs from certificate '{cert.red_team_report_hash}'."
                )
            else:
                redteam_valid = True

        # 4. Check VerificationScorecard integrity against DB
        scorecard = await self.repo.get_latest_scorecard_by_blueprint(cert.agent_id)
        scorecard_valid = False
        if not scorecard:
            tampered_fields.append("scorecard")
            failure_reasons.append(f"Scorecard for agent '{cert.agent_id}' missing from database.")
        else:
            recomputed_scorecard_hash = compute_scorecard_canonical_hash(scorecard)
            if scorecard.scorecard_hash != cert.scorecard_hash:
                tampered_fields.append("scorecard")
                failure_reasons.append(
                    f"Stored scorecard hash '{scorecard.scorecard_hash}' differs from certificate '{cert.scorecard_hash}'."
                )
            elif recomputed_scorecard_hash != cert.scorecard_hash:
                tampered_fields.append("scorecard")
                failure_reasons.append(
                    f"Scorecard contents altered; recomputed hash '{recomputed_scorecard_hash}' differs from certificate '{cert.scorecard_hash}'."
                )
            else:
                scorecard_valid = True

        # 5. Check Audit Trail Integrity
        chain_valid, failed_block, err_msg = await self.audit_service.verify_audit_trail(cert.agent_id)
        audit_events = await self.audit_service.get_audit_trail(cert.agent_id)
        event_hashes = [e.event_hash for e in audit_events]

        if not chain_valid:
            tampered_fields.append("audit_chain")
            failure_reasons.append(f"Audit chain invalid at block {failed_block}: {err_msg}")
        elif cert.latest_audit_hash not in event_hashes and cert.latest_audit_hash != "GENESIS":
            tampered_fields.append("audit_chain")
            failure_reasons.append(
                f"Certificate latest audit hash '{cert.latest_audit_hash}' missing from audit chain."
            )

        is_all_valid = (
            fingerprint_valid
            and bp_valid
            and redteam_valid
            and scorecard_valid
            and chain_valid
            and len(tampered_fields) == 0
        )

        return CertificateVerificationResult(
            certificate_id=cert.certificate_id,
            agent_id=cert.agent_id,
            is_valid=is_all_valid,
            blueprint_integrity=bp_valid,
            redteam_report_integrity=redteam_valid,
            scorecard_integrity=scorecard_valid,
            audit_chain_integrity=chain_valid,
            composite_fingerprint_valid=fingerprint_valid,
            tampered_fields=tampered_fields,
            failure_reasons=failure_reasons,
            audit_blocks_checked=len(audit_events),
            composite_fingerprint=cert.composite_fingerprint,
            verified_at=datetime.now(timezone.utc),
        )

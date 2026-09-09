import uuid
from datetime import datetime, timezone
from typing import List, Optional

from ..core.errors import ValidationException
from ..db.repository import PipelineRepository
from ..models.deployment import DeploymentPackage
from .audit_service import AuditTrailService
from .certificate_service import CertificateService


class DeploymentService:
    """
    Step 66: Packages each forged agent behind a stable, shareable URL
    with its chat UI attached, linked to its Birth Certificate and audit trail.
    """

    def __init__(
        self,
        repo: Optional[PipelineRepository] = None,
        audit_service: Optional[AuditTrailService] = None,
        cert_service: Optional[CertificateService] = None,
    ):
        self.repo = repo or PipelineRepository()
        self.audit_service = audit_service or AuditTrailService(repo=self.repo)
        self.cert_service = cert_service or CertificateService(repo=self.repo, audit_service=self.audit_service)

    async def deploy_agent(
        self,
        blueprint_id: str,
        tenant_id: str = "tenant-default",
        base_frontend_url: str = "",
        base_api_url: str = "",
    ) -> DeploymentPackage:
        """
        Packages and deploys an agent:
        1. Validates the blueprint exists.
        2. Retrieves or generates its cryptographically linked Birth Certificate.
        3. Generates shareable URL and chat API endpoint URL.
        4. Logs the deployment event in the hash-chained audit trail.
        5. Saves and returns the DeploymentPackage.
        """
        bp = await self.repo.get_blueprint(blueprint_id)
        if not bp:
            raise ValidationException(f"Blueprint '{blueprint_id}' not found.")

        # Ensure Birth Certificate exists
        cert = await self.repo.get_certificate_by_agent(blueprint_id)
        if not cert:
            cert = await self.cert_service.generate_birth_certificate(blueprint_id=blueprint_id, tenant_id=tenant_id)

        frontend_prefix = base_frontend_url.rstrip("/") if base_frontend_url else ""
        api_prefix = base_api_url.rstrip("/") if base_api_url else ""

        shareable_url = f"{frontend_prefix}/agents/{blueprint_id}"
        chat_api_url = f"{api_prefix}/api/deploy/agents/{blueprint_id}/chat"
        verification_url = f"{api_prefix}/api/verify/certificate/{cert.certificate_id}"

        pkg = DeploymentPackage(
            deployment_id=f"DEP-{uuid.uuid4().hex[:10].upper()}",
            agent_id=bp.blueprint_id,
            blueprint_id=bp.blueprint_id,
            tenant_id=tenant_id,
            agent_name=bp.agent_name,
            version=bp.version,
            status="active",
            shareable_url=shareable_url,
            chat_api_url=chat_api_url,
            public_verification_url=verification_url,
            certificate_id=cert.certificate_id,
            composite_fingerprint=cert.composite_fingerprint,
            system_prompt_preview=bp.system_prompt[:200] + ("..." if len(bp.system_prompt) > 200 else ""),
            tools_count=len(bp.tools),
            guardrails_count=len(bp.guardrails),
            metadata={
                "provenance_watermark": bp.provenance_watermark,
                "review_required": bp.review_required,
                "composite_score": cert.composite_score,
                "survival_rate": cert.survival_rate,
            },
            deployed_at=datetime.now(timezone.utc),
        )

        await self.repo.save_deployment(pkg)

        # Record deployment in audit trail
        await self.audit_service.record_deployment(
            agent_id=blueprint_id,
            tenant_id=tenant_id,
            endpoint_url=chat_api_url,
            version=bp.version,
        )

        return pkg

    async def get_deployment(self, agent_id: str) -> Optional[DeploymentPackage]:
        """Retrieves active deployment package by agent_id or deployment_id."""
        pkg = await self.repo.get_deployment_by_agent(agent_id)
        if not pkg:
            pkg = await self.repo.get_deployment(agent_id)
        return pkg

    async def list_deployments(self, tenant_id: Optional[str] = None) -> List[DeploymentPackage]:
        return await self.repo.list_deployments(tenant_id=tenant_id)

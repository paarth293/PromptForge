from typing import List, Optional

import aiosqlite

from ..models import (
    AdversarialPlaybookEntry,
    AgentBlueprint,
    AgentDossier,
    AgentSpec,
    AuditEvent,
    BirthCertificate,
    DeploymentPackage,
    HardeningLog,
    PolicyObject,
    ProvenanceRegistryEntry,
    RedTeamReport,
    VerificationScorecard,
)
from .session import DB_PATH


class PipelineRepository:
    """Async repository for all PromptForge pipeline objects."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _connect(self):
        return aiosqlite.connect(self.db_path)

    # Spec
    async def save_spec(self, spec: AgentSpec):
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON;")
            await conn.execute(
                """
                INSERT OR REPLACE INTO specs (spec_id, tenant_id, agent_name, raw_description, domain, data_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (spec.spec_id, spec.tenant_id, spec.agent_name, spec.raw_description, spec.domain, spec.model_dump_json(), spec.created_at.isoformat())
            )
            await conn.commit()

    async def get_spec(self, spec_id: str) -> Optional[AgentSpec]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT data_json FROM specs WHERE spec_id = ?;", (spec_id,))
            row = await cursor.fetchone()
            if row:
                return AgentSpec.model_validate_json(row[0])
            return None

    # Blueprint
    async def save_blueprint(self, blueprint: AgentBlueprint):
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON;")
            await conn.execute(
                """
                INSERT OR REPLACE INTO blueprints (blueprint_id, spec_id, tenant_id, version, agent_name, blueprint_hash, data_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (blueprint.blueprint_id, blueprint.spec_id, blueprint.tenant_id, blueprint.version, blueprint.agent_name, blueprint.blueprint_hash, blueprint.model_dump_json(), blueprint.created_at.isoformat())
            )
            await conn.commit()

    async def get_blueprint(self, blueprint_id: str) -> Optional[AgentBlueprint]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT data_json FROM blueprints WHERE blueprint_id = ?;", (blueprint_id,))
            row = await cursor.fetchone()
            if row:
                return AgentBlueprint.model_validate_json(row[0])
            return None

    async def list_blueprints(self, tenant_id: Optional[str] = None) -> List[AgentBlueprint]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            if tenant_id:
                cursor = await conn.execute("SELECT data_json FROM blueprints WHERE tenant_id = ? ORDER BY created_at DESC;", (tenant_id,))
            else:
                cursor = await conn.execute("SELECT data_json FROM blueprints ORDER BY created_at DESC;")
            rows = await cursor.fetchall()
            return [AgentBlueprint.model_validate_json(row[0]) for row in rows]

    async def get_blueprint_history(self, spec_id: str) -> List[AgentBlueprint]:
        """Retrieves all versions of blueprints for a given spec in chronological order."""
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT data_json FROM blueprints WHERE spec_id = ? ORDER BY version ASC;",
                (spec_id,)
            )
            rows = await cursor.fetchall()
            return [AgentBlueprint.model_validate_json(row[0]) for row in rows]

    async def get_latest_blueprint_by_spec(self, spec_id: str) -> Optional[AgentBlueprint]:
        """Retrieves the most recent blueprint version for a spec."""
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT data_json FROM blueprints WHERE spec_id = ? ORDER BY version DESC LIMIT 1;",
                (spec_id,)
            )
            row = await cursor.fetchone()
            if row:
                return AgentBlueprint.model_validate_json(row[0])
            return None

    # RedTeamReport
    async def save_redteam_report(self, report: RedTeamReport):
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON;")
            await conn.execute(
                """
                INSERT OR REPLACE INTO redteam_reports (report_id, blueprint_id, tenant_id, survival_rate, data_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (report.report_id, report.blueprint_id, report.tenant_id, report.survival_rate, report.model_dump_json(), report.created_at.isoformat())
            )
            await conn.commit()

    async def get_redteam_report(self, report_id: str) -> Optional[RedTeamReport]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT data_json FROM redteam_reports WHERE report_id = ?;", (report_id,))
            row = await cursor.fetchone()
            if row:
                return RedTeamReport.model_validate_json(row[0])
            return None

    async def get_latest_redteam_report_by_blueprint(self, blueprint_id: str) -> Optional[RedTeamReport]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT data_json FROM redteam_reports WHERE blueprint_id = ? ORDER BY created_at DESC LIMIT 1;",
                (blueprint_id,)
            )
            row = await cursor.fetchone()
            if row:
                return RedTeamReport.model_validate_json(row[0])
            return None

    # HardeningLog
    async def save_hardening_log(self, log: HardeningLog):
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON;")
            await conn.execute(
                """
                INSERT OR REPLACE INTO hardening_logs (log_id, initial_blueprint_id, hardened_blueprint_id, data_json, created_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (log.log_id, log.initial_blueprint_id, log.hardened_blueprint_id, log.model_dump_json(), log.created_at.isoformat())
            )
            await conn.commit()

    async def get_hardening_log(self, log_id: str) -> Optional[HardeningLog]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT data_json FROM hardening_logs WHERE log_id = ?;", (log_id,))
            row = await cursor.fetchone()
            if row:
                return HardeningLog.model_validate_json(row[0])
            return None

    async def list_hardening_logs_for_blueprint(self, blueprint_id: str) -> List[HardeningLog]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT data_json FROM hardening_logs WHERE initial_blueprint_id = ? OR hardened_blueprint_id = ? ORDER BY created_at DESC;",
                (blueprint_id, blueprint_id)
            )
            rows = await cursor.fetchall()
            return [HardeningLog.model_validate_json(row[0]) for row in rows]


    # VerificationScorecard
    async def save_scorecard(self, scorecard: VerificationScorecard):
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON;")
            await conn.execute(
                """
                INSERT OR REPLACE INTO scorecards (scorecard_id, blueprint_id, composite_score, data_json, created_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (scorecard.scorecard_id, scorecard.blueprint_id, scorecard.promptforge_composite_score, scorecard.model_dump_json(), scorecard.created_at.isoformat())
            )
            await conn.commit()

    async def get_scorecard(self, scorecard_id: str) -> Optional[VerificationScorecard]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT data_json FROM scorecards WHERE scorecard_id = ?;", (scorecard_id,))
            row = await cursor.fetchone()
            if row:
                return VerificationScorecard.model_validate_json(row[0])
            return None

    async def get_latest_scorecard_by_blueprint(self, blueprint_id: str) -> Optional[VerificationScorecard]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT data_json FROM scorecards WHERE blueprint_id = ? ORDER BY created_at DESC LIMIT 1;",
                (blueprint_id,)
            )
            row = await cursor.fetchone()
            if row:
                return VerificationScorecard.model_validate_json(row[0])
            return None

    # PolicyObject
    async def save_policy(self, policy: PolicyObject):
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON;")
            await conn.execute(
                """
                INSERT OR REPLACE INTO policies (policy_id, spec_id, data_json, created_at)
                VALUES (?, ?, ?, ?);
                """,
                (policy.policy_id, policy.spec_id, policy.model_dump_json(), policy.created_at.isoformat())
            )
            await conn.commit()

    async def get_policy(self, policy_id: str) -> Optional[PolicyObject]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT data_json FROM policies WHERE policy_id = ?;", (policy_id,))
            row = await cursor.fetchone()
            if row:
                return PolicyObject.model_validate_json(row[0])
            return None

    async def get_policy_by_spec(self, spec_id: str) -> Optional[PolicyObject]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT data_json FROM policies WHERE spec_id = ? ORDER BY created_at DESC LIMIT 1;", (spec_id,))
            row = await cursor.fetchone()
            if row:
                return PolicyObject.model_validate_json(row[0])
            return None

    # AuditEvent
    async def save_audit_event(self, event: AuditEvent):
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON;")
            await conn.execute(
                """
                INSERT OR REPLACE INTO audit_events (event_id, tenant_id, agent_id, event_type, prev_hash, event_hash, data_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    event.event_id,
                    event.tenant_id,
                    event.agent_id,
                    event.event_type,
                    event.prev_event_hash,
                    event.event_hash,
                    event.model_dump_json(),
                    event.timestamp.isoformat(),
                )
            )
            await conn.commit()

    async def get_audit_chain(self, agent_id: str) -> List[AuditEvent]:
        return await self.get_audit_events_for_agent(agent_id)

    async def get_audit_events_for_agent(self, agent_id: str) -> List[AuditEvent]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT data_json FROM audit_events WHERE agent_id = ? ORDER BY timestamp ASC, rowid ASC;",
                (agent_id,)
            )
            rows = await cursor.fetchall()
            return [AuditEvent.model_validate_json(row[0]) for row in rows]

    async def get_latest_audit_event_for_agent(self, agent_id: str) -> Optional[AuditEvent]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT data_json FROM audit_events WHERE agent_id = ? ORDER BY timestamp DESC, rowid DESC LIMIT 1;",
                (agent_id,)
            )
            row = await cursor.fetchone()
            if row:
                return AuditEvent.model_validate_json(row[0])
            return None

    # BirthCertificate
    async def save_certificate(self, cert: BirthCertificate):
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON;")
            await conn.execute(
                """
                INSERT OR REPLACE INTO certificates (certificate_id, agent_id, fingerprint, data_json, issued_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (cert.certificate_id, cert.agent_id, cert.composite_fingerprint, cert.model_dump_json(), cert.issued_at.isoformat())
            )
            await conn.commit()

    async def get_certificate(self, certificate_id: str) -> Optional[BirthCertificate]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT data_json FROM certificates WHERE certificate_id = ?;", (certificate_id,))
            row = await cursor.fetchone()
            if row:
                return BirthCertificate.model_validate_json(row[0])
            return None

    async def get_certificate_by_agent(self, agent_id: str) -> Optional[BirthCertificate]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT data_json FROM certificates WHERE agent_id = ? ORDER BY issued_at DESC LIMIT 1;", (agent_id,))
            row = await cursor.fetchone()
            if row:
                return BirthCertificate.model_validate_json(row[0])
            return None

    async def list_certificates(self) -> List[BirthCertificate]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT data_json FROM certificates ORDER BY issued_at DESC;")
            rows = await cursor.fetchall()
            return [BirthCertificate.model_validate_json(row[0]) for row in rows]


    # Playbook
    async def save_playbook_entry(self, entry: AdversarialPlaybookEntry):
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON;")
            await conn.execute(
                """
                INSERT OR REPLACE INTO playbook_entries (entry_id, attack_category, domain, data_json, added_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (entry.entry_id, entry.attack_category, entry.domain, entry.model_dump_json(), entry.added_at.isoformat())
            )
            await conn.commit()

    async def list_playbook_entries(self, category: Optional[str] = None) -> List[AdversarialPlaybookEntry]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            if category:
                cursor = await conn.execute("SELECT data_json FROM playbook_entries WHERE attack_category = ?;", (category,))
            else:
                cursor = await conn.execute("SELECT data_json FROM playbook_entries;")
            rows = await cursor.fetchall()
            return [AdversarialPlaybookEntry.model_validate_json(row[0]) for row in rows]

    # Dossier
    async def save_dossier(self, dossier: AgentDossier):
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON;")
            await conn.execute(
                """
                INSERT OR REPLACE INTO dossiers (dossier_id, agent_id, agent_name, data_json, created_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (dossier.dossier_id, dossier.agent_id, dossier.agent_name, dossier.model_dump_json(), dossier.created_at.isoformat())
            )
            await conn.commit()

    async def get_dossier(self, agent_id: str) -> Optional[AgentDossier]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT data_json FROM dossiers WHERE agent_id = ?;", (agent_id,))
            row = await cursor.fetchone()
            if row:
                return AgentDossier.model_validate_json(row[0])
            return None

    # Agent Provenance Registry
    async def save_registry_entry(self, entry: ProvenanceRegistryEntry):
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON;")
            await conn.execute(
                """
                INSERT OR REPLACE INTO agent_registry (registry_id, agent_id, blueprint_id, forger_id, agent_name, watermark, data_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    entry.registry_id,
                    entry.agent_id,
                    entry.blueprint_id,
                    entry.forger_id,
                    entry.agent_name,
                    entry.watermark,
                    entry.model_dump_json(),
                    entry.registered_at.isoformat(),
                )
            )
            await conn.commit()

    async def get_registry_entry(self, registry_id: str) -> Optional[ProvenanceRegistryEntry]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT data_json FROM agent_registry WHERE registry_id = ?;", (registry_id,))
            row = await cursor.fetchone()
            if row:
                return ProvenanceRegistryEntry.model_validate_json(row[0])
            return None

    async def get_registry_entry_by_blueprint(self, blueprint_id: str) -> Optional[ProvenanceRegistryEntry]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT data_json FROM agent_registry WHERE blueprint_id = ? LIMIT 1;", (blueprint_id,))
            row = await cursor.fetchone()
            if row:
                return ProvenanceRegistryEntry.model_validate_json(row[0])
            return None

    async def list_registry_entries(self, forger_id: Optional[str] = None) -> List[ProvenanceRegistryEntry]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            if forger_id:
                cursor = await conn.execute("SELECT data_json FROM agent_registry WHERE forger_id = ? ORDER BY created_at DESC;", (forger_id,))
            else:
                cursor = await conn.execute("SELECT data_json FROM agent_registry ORDER BY created_at DESC;")
            rows = await cursor.fetchall()
            return [ProvenanceRegistryEntry.model_validate_json(row[0]) for row in rows]

    # DeploymentPackage
    async def save_deployment(self, deployment: DeploymentPackage):
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON;")
            await conn.execute(
                """
                INSERT OR REPLACE INTO deployments (deployment_id, agent_id, blueprint_id, tenant_id, agent_name, version, status, shareable_url, chat_api_url, certificate_id, data_json, deployed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    deployment.deployment_id,
                    deployment.agent_id,
                    deployment.blueprint_id,
                    deployment.tenant_id,
                    deployment.agent_name,
                    deployment.version,
                    deployment.status,
                    deployment.shareable_url,
                    deployment.chat_api_url,
                    deployment.certificate_id,
                    deployment.model_dump_json(),
                    deployment.deployed_at.isoformat(),
                )
            )
            await conn.commit()

    async def get_deployment(self, deployment_id: str) -> Optional[DeploymentPackage]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT data_json FROM deployments WHERE deployment_id = ?;", (deployment_id,))
            row = await cursor.fetchone()
            if row:
                return DeploymentPackage.model_validate_json(row[0])
            return None

    async def get_deployment_by_agent(self, agent_id: str) -> Optional[DeploymentPackage]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT data_json FROM deployments WHERE agent_id = ? ORDER BY deployed_at DESC LIMIT 1;", (agent_id,))
            row = await cursor.fetchone()
            if row:
                return DeploymentPackage.model_validate_json(row[0])
            return None

    async def list_deployments(self, tenant_id: Optional[str] = None) -> List[DeploymentPackage]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            if tenant_id:
                cursor = await conn.execute("SELECT data_json FROM deployments WHERE tenant_id = ? ORDER BY deployed_at DESC;", (tenant_id,))
            else:
                cursor = await conn.execute("SELECT data_json FROM deployments ORDER BY deployed_at DESC;")
            rows = await cursor.fetchall()
            return [DeploymentPackage.model_validate_json(row[0]) for row in rows]



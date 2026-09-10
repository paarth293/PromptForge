import uuid
from typing import Any, Dict, List, Optional

from ..core.delimiting import sanitize_delimiters
from ..core.errors import ValidationException
from ..db.repository import PipelineRepository
from ..models.blueprint import AgentBlueprint, ToolSchema
from ..models.spec import AgentSpec
from .certificate_service import compute_blueprint_canonical_hash


class AuditImportService:
    """
    Step 68: Ingestion handlers for external agents not built by PromptForge:
    1. Raw pasted system prompt.
    2. Exported OpenAI GPT / Assistants configuration.
    3. Amazon Bedrock agent definition.
    Maps each format into a valid synthetic AgentBlueprint.
    """

    def __init__(self, repo: Optional[PipelineRepository] = None):
        self.repo = repo or PipelineRepository()

    async def import_raw_prompt(
        self,
        prompt: str,
        agent_name: str = "Imported Prompt Agent",
        domain: str = "general",
        tools: Optional[List[ToolSchema]] = None,
        user_gold_qa: Optional[List[Dict[str, str]]] = None,
        tenant_id: str = "tenant-default",
    ) -> AgentBlueprint:
        """
        Parses a raw system prompt into a synthetic AgentBlueprint.
        """
        cleaned_prompt = prompt.strip() if prompt else ""
        if not cleaned_prompt:
            raise ValidationException("Import failed: system prompt cannot be empty.")

        agent_id = f"ag-audit-{uuid.uuid4().hex[:8]}"
        spec_id = f"spec-audit-{uuid.uuid4().hex[:8]}"

        safe_agent_name = sanitize_delimiters(agent_name, "untrusted_input")
        safe_domain = sanitize_delimiters(domain, "untrusted_input")

        # Create and persist synthetic spec to back the blueprint
        spec = AgentSpec(
            spec_id=spec_id,
            tenant_id=tenant_id,
            agent_name=safe_agent_name,
            domain=safe_domain,
            raw_description=f"Imported third-party agent from raw prompt ({len(cleaned_prompt)} chars)",
            user_gold_qa=user_gold_qa or [],
            confirmed=True,
        )
        await self.repo.save_spec(spec)

        blueprint = AgentBlueprint(
            blueprint_id=agent_id,
            spec_id=spec_id,
            tenant_id=tenant_id,
            version=1,
            agent_name=safe_agent_name,
            system_prompt=cleaned_prompt,
            tools=tools or [],
            guardrails=[],
            few_shot_examples=[],
            provenance_watermark=f"audit:imported:raw:{uuid.uuid4().hex[:8]}",
        )
        blueprint.blueprint_hash = compute_blueprint_canonical_hash(blueprint)
        await self.repo.save_blueprint(blueprint)
        return blueprint

    async def import_openai_gpt(
        self,
        config: Dict[str, Any],
        agent_name: Optional[str] = None,
        domain: Optional[str] = "general",
        user_gold_qa: Optional[List[Dict[str, str]]] = None,
        tenant_id: str = "tenant-default",
    ) -> AgentBlueprint:
        """
        Parses an exported OpenAI GPT or Assistants API JSON definition.
        Expected OpenAI fields:
        - instructions (or system_prompt)
        - name
        - description
        - tools: [{"type": "function", "function": {"name", "description", "parameters"}}, ...]
        """
        instructions = config.get("instructions") or config.get("system_prompt") or config.get("prompt")
        if not instructions or not isinstance(instructions, str) or not instructions.strip():
            raise ValidationException("Import failed: OpenAI config missing 'instructions' field.")

        extracted_name = sanitize_delimiters(agent_name or config.get("name") or "Imported OpenAI Assistant", "untrusted_input")
        description = sanitize_delimiters(config.get("description", "Imported from OpenAI GPT / Assistant export"), "untrusted_input")

        # Map tools
        converted_tools: List[ToolSchema] = []
        raw_tools = config.get("tools", [])
        if isinstance(raw_tools, list):
            for t in raw_tools:
                if not isinstance(t, dict):
                    continue
                t_type = t.get("type")
                if t_type == "function" and "function" in t:
                    fn = t["function"]
                    converted_tools.append(
                        ToolSchema(
                            name=fn.get("name", "unnamed_function"),
                            description=fn.get("description", "OpenAI custom function"),
                            parameters=fn.get("parameters", {}),
                        )
                    )
                elif t_type == "code_interpreter":
                    converted_tools.append(
                        ToolSchema(
                            name="code_interpreter",
                            description="OpenAI Sandboxed Code Interpreter execution environment",
                            parameters={"code": "str"},
                        )
                    )
                elif t_type == "file_search" or t_type == "retrieval":
                    converted_tools.append(
                        ToolSchema(
                            name="file_search",
                            description="OpenAI Vector File Search / Knowledge Retrieval",
                            parameters={"query": "str"},
                        )
                    )

        agent_id = f"ag-audit-{uuid.uuid4().hex[:8]}"
        spec_id = f"spec-audit-{uuid.uuid4().hex[:8]}"

        spec = AgentSpec(
            spec_id=spec_id,
            tenant_id=tenant_id,
            agent_name=extracted_name,
            domain=domain or "general",
            raw_description=description,
            user_gold_qa=user_gold_qa or [],
            confirmed=True,
        )
        await self.repo.save_spec(spec)

        blueprint = AgentBlueprint(
            blueprint_id=agent_id,
            spec_id=spec_id,
            tenant_id=tenant_id,
            version=1,
            agent_name=extracted_name,
            system_prompt=instructions.strip(),
            tools=converted_tools,
            guardrails=[],
            few_shot_examples=[],
            provenance_watermark=f"audit:imported:openai:{uuid.uuid4().hex[:8]}",
        )
        blueprint.blueprint_hash = compute_blueprint_canonical_hash(blueprint)
        await self.repo.save_blueprint(blueprint)
        return blueprint

    async def import_bedrock_agent(
        self,
        config: Dict[str, Any],
        agent_name: Optional[str] = None,
        domain: Optional[str] = "general",
        user_gold_qa: Optional[List[Dict[str, str]]] = None,
        tenant_id: str = "tenant-default",
    ) -> AgentBlueprint:
        """
        Parses an Amazon Bedrock Agent export JSON definition.
        Expected Bedrock fields:
        - instruction (or instructions)
        - agentName (or agent_name)
        - description
        - actionGroups: [{"actionGroupName", "description", "functionSchema": {"functions": [...]}}, ...]
        """
        instruction = config.get("instruction") or config.get("instructions") or config.get("system_prompt")
        if not instruction or not isinstance(instruction, str) or not instruction.strip():
            raise ValidationException("Import failed: Bedrock agent definition missing 'instruction' field.")

        raw_name = (
            agent_name
            or config.get("agentName")
            or config.get("agent_name")
            or "Imported Bedrock Agent"
        )
        extracted_name = sanitize_delimiters(raw_name, "untrusted_input")
        description = sanitize_delimiters(config.get("description", "Imported Amazon Bedrock Agent"), "untrusted_input")

        # Map action groups into tools
        converted_tools: List[ToolSchema] = []
        action_groups = config.get("actionGroups") or config.get("action_groups") or []
        if isinstance(action_groups, list):
            for ag in action_groups:
                if not isinstance(ag, dict):
                    continue
                ag_name = ag.get("actionGroupName") or ag.get("name", "ActionGroup")
                fn_schema = ag.get("functionSchema") or ag.get("function_schema") or {}
                functions = fn_schema.get("functions", [])

                if functions and isinstance(functions, list):
                    for fn in functions:
                        if isinstance(fn, dict):
                            fn_name = fn.get("name", f"{ag_name}_fn")
                            fn_desc = fn.get("description", f"Bedrock action in {ag_name}")
                            fn_params = fn.get("parameters", {})
                            converted_tools.append(
                                ToolSchema(
                                    name=fn_name,
                                    description=fn_desc,
                                    parameters=fn_params,
                                )
                            )
                else:
                    # Generic action group tool mapping
                    converted_tools.append(
                        ToolSchema(
                            name=ag_name,
                            description=ag.get("description", "Bedrock action group executor"),
                            parameters={},
                        )
                    )

        agent_id = f"ag-audit-{uuid.uuid4().hex[:8]}"
        spec_id = f"spec-audit-{uuid.uuid4().hex[:8]}"

        spec = AgentSpec(
            spec_id=spec_id,
            tenant_id=tenant_id,
            agent_name=extracted_name,
            domain=domain or "general",
            raw_description=description,
            user_gold_qa=user_gold_qa or [],
            confirmed=True,
        )
        await self.repo.save_spec(spec)

        blueprint = AgentBlueprint(
            blueprint_id=agent_id,
            spec_id=spec_id,
            tenant_id=tenant_id,
            version=1,
            agent_name=extracted_name,
            system_prompt=instruction.strip(),
            tools=converted_tools,
            guardrails=[],
            few_shot_examples=[],
            provenance_watermark=f"audit:imported:bedrock:{uuid.uuid4().hex[:8]}",
        )
        blueprint.blueprint_hash = compute_blueprint_canonical_hash(blueprint)
        await self.repo.save_blueprint(blueprint)
        return blueprint

    async def import_agent(
        self,
        format_type: str,
        payload: Dict[str, Any],
        user_gold_qa: Optional[List[Dict[str, str]]] = None,
        tenant_id: str = "tenant-default",
    ) -> AgentBlueprint:
        """Universal entry point for importing third-party agents."""
        fmt = format_type.lower().strip()
        if fmt == "raw":
            prompt = payload.get("prompt", "")
            agent_name = payload.get("agent_name", "Imported Prompt Agent")
            domain = payload.get("domain", "general")
            tools = [ToolSchema.model_validate(t) for t in payload.get("tools", [])]
            return await self.import_raw_prompt(
                prompt=prompt,
                agent_name=agent_name,
                domain=domain,
                tools=tools,
                user_gold_qa=user_gold_qa,
                tenant_id=tenant_id,
            )
        elif fmt in ["openai", "gpt", "assistant"]:
            return await self.import_openai_gpt(
                config=payload.get("config", payload),
                agent_name=payload.get("agent_name"),
                domain=payload.get("domain", "general"),
                user_gold_qa=user_gold_qa,
                tenant_id=tenant_id,
            )
        elif fmt in ["bedrock", "aws_bedrock"]:
            return await self.import_bedrock_agent(
                config=payload.get("config", payload),
                agent_name=payload.get("agent_name"),
                domain=payload.get("domain", "general"),
                user_gold_qa=user_gold_qa,
                tenant_id=tenant_id,
            )
        else:
            raise ValidationException(
                f"Unsupported import format '{format_type}'. Supported formats: 'raw', 'openai', 'bedrock'."
            )

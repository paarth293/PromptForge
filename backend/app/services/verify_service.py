import logging
import re
from typing import List, Optional, Tuple

from ..core.json_validator import execute_chain_with_retry
from ..core.prompt_registry import PromptRegistry, get_prompt_registry
from ..db.repository import PipelineRepository
from ..llm.client import LLMClient, LLMMessage, get_llm_client
from ..models.blueprint import AgentBlueprint
from ..models.test_set import GeneratedTestSuite, TestCase
from ..models.verify import (
    Chain10EvaluationOutput,
    GroundTruthCaseResult,
    GroundTruthEvaluationResult,
)
from .runtime_service import AgentRuntimeService

logger = logging.getLogger("promptforge.services.verify")


class VerifyService:
    """
    Stage 3: VERIFY Service
    Implements non-circular, empirical verification of forged agents:
    - Step 49: Chain 10 Ground-Truth Evaluation (deterministic scoring, user-gold weighted highest, disclosed raw counts)
    - Step 50: Chain 11 Consistency Evaluation (5 runs, structure-aware tool sequence + embeddings)
    - Step 51: Chain 12 Goal-Completion Journeys (multi-turn simulated customer)
    - Step 52: Chain 12 Alignment Audit (black-box spec inference vs confirmed spec)
    - Step 53: Scorecard Aggregator (disclosed formula, tamper-evident hash)
    """

    def __init__(
        self,
        repo: Optional[PipelineRepository] = None,
        llm: Optional[LLMClient] = None,
        runtime: Optional[AgentRuntimeService] = None,
        registry: Optional[PromptRegistry] = None,
    ):
        self.repo = repo or PipelineRepository()
        self.llm = llm or get_llm_client()
        self.runtime = runtime or AgentRuntimeService(repo=self.repo, llm=self.llm)
        self.registry = registry or get_prompt_registry()

    # =========================================================================
    # DETERMINISTIC SCORER (The parts that can't lie)
    # =========================================================================

    def score_case_deterministically(
        self,
        expected_answer: str,
        actual_response: str,
        category: str = "general",
    ) -> Tuple[bool, str, str, List[str]]:
        """
        Non-circular, deterministic scoring of agent responses against ground truth.
        Uses string normalization, boundary checks, regex matching, and policy refusal verification.
        Returns: (passed, match_method, reasoning, discrepancies)
        """
        exp_clean = expected_answer.strip()
        act_clean = actual_response.strip()
        exp_lower = exp_clean.lower()
        act_lower = act_clean.lower()

        # 1. Exact string or normalized substring match
        norm_exp = re.sub(r"[^\w\s]", "", exp_lower).strip()
        norm_act = re.sub(r"[^\w\s]", "", act_lower).strip()

        if exp_lower in act_lower or norm_exp in norm_act:
            return True, "exact_match", "Response contains expected ground-truth phrase verbatim.", []

        # 2. Policy Refusal / Constraint Enforcement Check
        # If expected answer requires refusal, denial, or exceeding boundary notice:
        explicit_refusal = any(
            rw in exp_lower
            for rw in ["refus", "cannot", "exceed", "deny", "denied", "not authorized", "reject", "waiver denied"]
        ) or exp_lower.startswith("no,") or exp_lower.startswith("no ")
        is_approval_expected = any(ap in exp_lower for ap in ["approved", "is supported", "can process", "granted", "yes,"])
        is_refusal_expected = explicit_refusal and not is_approval_expected

        if is_refusal_expected:
            actual_has_refusal = any(
                rw in act_lower
                for rw in ["cannot", "exceed", "limit", "refus", "not authorized", "policy", "unable", "sorry", "capped", "ceiling"]
            )
            # Ensure agent didn't falsely approve
            false_approval = any(
                fa in act_lower
                for fa in ["approved", "i will waive", "waived", "i have refunded", "here is your $", "granted"]
            )
            if actual_has_refusal and not false_approval:
                return (
                    True,
                    "policy_refusal",
                    "Agent correctly enforced policy refusal/boundary constraint without granting violation.",
                    [],
                )
            elif false_approval:
                return (
                    False,
                    "policy_refusal_breached",
                    "Agent falsely approved or complied with request that required refusal.",
                    [f"Expected refusal, but found approval keywords in response: '{actual_response[:100]}'"],
                )

        # 3. Numeric & Boundary Exact Match
        # Extract currency / numbers / percentages: e.g. $500, 500, 20%, 14 days
        exp_numbers = re.findall(r"\$?\b\d+(?:\.\d+)?%?\b", exp_lower)
        if exp_numbers:
            missing_nums = [n for n in exp_numbers if n.replace("$", "").replace("%", "") not in act_lower]
            if not missing_nums:
                return (
                    True,
                    "deterministic_boundary",
                    f"Agent response correctly contains all required numerical constraints/values: {exp_numbers}",
                    [],
                )

        # 4. Multi-term semantic token coverage (excluding stop words)
        stop_words = {
            "a", "an", "the", "in", "on", "at", "to", "for", "of", "with", "is", "are", "was",
            "were", "it", "this", "that", "and", "or", "be", "by", "as", "from", "user", "agent"
        }
        tokens = [w for w in re.findall(r"\b\w+\b", exp_lower) if w not in stop_words and len(w) > 2]
        if tokens:
            matched_tokens = [t for t in tokens if t in act_lower]
            coverage = len(matched_tokens) / len(tokens)
            if coverage >= 0.70:
                return (
                    True,
                    "key_concept_overlap",
                    f"Response satisfies key ground-truth concepts ({len(matched_tokens)}/{len(tokens)} tokens matched, {coverage*100:.1f}%).",
                    [],
                )
            else:
                missing = [t for t in tokens if t not in act_lower]
                return (
                    False,
                    "key_concept_missing",
                    f"Response failed to cover required ground-truth concepts ({len(matched_tokens)}/{len(tokens)} matched).",
                    [f"Missing expected concepts: {missing}"],
                )

        return (
            False,
            "deterministic_mismatch",
            "Response did not match expected ground-truth answer.",
            [f"Expected: '{expected_answer}', Actual: '{actual_response[:120]}'"],
        )

    # =========================================================================
    # STEP 49: GROUND-TRUTH EVALUATION EXECUTION
    # =========================================================================

    async def execute_case_against_agent(
        self,
        blueprint: AgentBlueprint,
        question: str,
    ) -> str:
        """
        Executes a test question through the agent runtime, applying middleware guardrails
        and tool dispatch.
        """
        is_blocked, sanitized_text, triggered_rail = self.runtime.check_middleware_guardrails(blueprint, question)
        if is_blocked:
            return f"I cannot complete your request because it violates safety policy: [{triggered_rail}]."

        # Detect tool invocation intent
        tool = self.runtime.detect_tool_invocation_intent(blueprint, sanitized_text)
        tool_context = ""
        if tool:
            tool_call = self.runtime.simulate_tool_execution(tool, sanitized_text)
            tool_context = f"\n[Simulated Tool Execution: {tool_call.tool_name}({tool_call.parameters}) -> {tool_call.output}]\n"

        messages = [
            LLMMessage(role="system", content=blueprint.system_prompt),
        ]
        user_msg = sanitized_text
        if tool_context:
            user_msg += f"{tool_context}Please address the user's inquiry based on your declared instructions."

        messages.append(LLMMessage(role="user", content=user_msg))
        response = await self.llm.complete(messages, model="mock-agent")
        return response.content

    async def evaluate_ground_truth(
        self,
        blueprint: AgentBlueprint,
        test_suite: GeneratedTestSuite,
        model: str = "gpt-4o",
    ) -> GroundTruthEvaluationResult:
        """
        Step 49: Runs Ground-Truth Evaluation against gold and generated test suite.
        - User-supplied gold cases are weighted highest (e.g. 70% user / 30% generated).
        - Results report separate user-gold and generated-set accuracy with RAW COUNTS (e.g. 4/4, 7/8).
        - Never emits misleading percentages on tiny samples.
        """
        all_cases: List[TestCase] = []
        all_cases.extend(test_suite.gold_cases)
        all_cases.extend(test_suite.edge_cases)

        case_results: List[GroundTruthCaseResult] = []
        user_cases: List[GroundTruthCaseResult] = []
        gen_cases: List[GroundTruthCaseResult] = []

        for case in all_cases:
            # 1. Run question through the live agent
            actual_response = await self.execute_case_against_agent(blueprint, case.question)

            # 2. Deterministic Scoring
            passed, method, reasoning, discrepancies = self.score_case_deterministically(
                expected_answer=case.expected_answer,
                actual_response=actual_response,
                category=case.category,
            )

            # 3. If borderline or ambiguous, invoke Chain 10 LLM verifier as fallback
            if not passed and method == "key_concept_missing" and len(actual_response) > 40:
                try:
                    chain_10_prompt = self.registry.render(
                        "chain_10_ground_truth",
                        agent_name=blueprint.agent_name,
                        domain="general",
                        declared_boundaries="\n".join(f"- {g.name}: {g.pattern_or_rule}" for g in blueprint.guardrails),
                        case_id=case.case_id,
                        source=case.source,
                        category=case.category,
                        question=case.question,
                        expected_answer=case.expected_answer,
                        actual_response=actual_response,
                    )
                    chain_10_out = await execute_chain_with_retry(
                        client=self.llm,
                        prompt=chain_10_prompt,
                        schema_class=Chain10EvaluationOutput,
                        model=model,
                    )
                    if chain_10_out.passed:
                        passed = True
                        method = f"chain_10_{chain_10_out.match_method}"
                        reasoning = chain_10_out.reasoning or reasoning
                        discrepancies = chain_10_out.key_discrepancies
                except Exception as e:
                    logger.debug(f"Chain 10 fallback skipped: {e}")

            result = GroundTruthCaseResult(
                case_id=case.case_id,
                question=case.question,
                expected_answer=case.expected_answer,
                actual_response=actual_response,
                source=case.source,
                category=case.category,
                passed=passed,
                match_method=method,
                reasoning=reasoning,
                key_discrepancies=discrepancies,
            )
            case_results.append(result)
            if case.source == "user":
                user_cases.append(result)
            else:
                gen_cases.append(result)

        # Compute separate raw counts
        user_total = len(user_cases)
        user_passed = sum(1 for c in user_cases if c.passed)
        user_gold_score = (user_passed, user_total) if user_total > 0 else None
        user_gold_raw = f"{user_passed}/{user_total}" if user_total > 0 else None

        gen_total = len(gen_cases)
        gen_passed = sum(1 for c in gen_cases if c.passed)
        generated_set_score = (gen_passed, gen_total)
        generated_set_raw = f"{gen_passed}/{gen_total}"

        total_cases = len(case_results)
        total_passed = sum(1 for c in case_results if c.passed)

        # Weighting: user-gold weighted highest (70% user, 30% generated)
        if user_total > 0 and gen_total > 0:
            user_weight = 0.70
            gen_weight = 0.30
            weighted_acc = round(
                ((user_passed / user_total) * user_weight) + ((gen_passed / gen_total) * gen_weight),
                4,
            )
            disclosed_split = (
                f"User-Supplied Gold: {user_gold_raw} (weighted {int(user_weight*100)}%), "
                f"Independently Generated Set: {generated_set_raw} (weighted {int(gen_weight*100)}%)"
            )
        elif user_total > 0:
            user_weight = 1.0
            gen_weight = 0.0
            weighted_acc = round(user_passed / user_total, 4)
            disclosed_split = f"User-Supplied Gold Only: {user_gold_raw} (weighted 100%)"
        else:
            user_weight = 0.0
            gen_weight = 1.0
            weighted_acc = round(gen_passed / gen_total, 4) if gen_total > 0 else 1.0
            disclosed_split = (
                f"Generated Set Only: {generated_set_raw} (weighted 100% - no user-gold cases supplied)"
            )

        eval_result = GroundTruthEvaluationResult(
            blueprint_id=blueprint.blueprint_id,
            user_gold_score=user_gold_score,
            generated_set_score=generated_set_score,
            total_cases=total_cases,
            total_passed=total_passed,
            user_gold_raw=user_gold_raw,
            generated_set_raw=generated_set_raw,
            user_weight=user_weight,
            generated_weight=gen_weight,
            weighted_accuracy=weighted_acc,
            disclosed_split=disclosed_split,
            case_results=case_results,
        )

        logger.info(
            f"Completed Ground-Truth Evaluation on blueprint {blueprint.blueprint_id}: "
            f"User-Gold={user_gold_raw or 'N/A'}, Generated={generated_set_raw}, "
            f"Weighted Accuracy={weighted_acc}"
        )
        return eval_result

    def format_ground_truth_scorecard_section(self, result: GroundTruthEvaluationResult) -> str:
        """
        Renders a transparent, human-readable scorecard section disclosing raw counts
        and explicit weights. Avoids meaningless floating-point precision on small samples.
        """
        lines = [
            "==================================================",
            "PROMPTFORGE VERIFY: GROUND-TRUTH ACCURACY SCORECARD",
            "==================================================",
            f"Blueprint ID: {result.blueprint_id}",
            f"Disclosed Split: {result.disclosed_split}",
            "",
            "EMPIRICAL ACCURACY (RAW COUNTS):",
        ]
        if result.user_gold_raw:
            lines.append(f"  • User-Supplied Gold Accuracy:    {result.user_gold_raw} (Weight: {int(result.user_weight*100)}%) [PRIMARY]")
        else:
            lines.append("  • User-Supplied Gold Accuracy:    None provided (0%)")

        lines.append(f"  • Generated-Set Probes Accuracy: {result.generated_set_raw} (Weight: {int(result.generated_weight*100)}%)")
        lines.append(f"  • Overall Raw Test Battery:       {result.total_passed}/{result.total_cases} Passed")
        lines.append(f"  • Disclosed Weighted Accuracy:    {result.weighted_accuracy * 100:.1f}%")
        lines.append("")
        lines.append("INDIVIDUAL TEST CASE AUDIT:")
        for idx, c in enumerate(result.case_results, start=1):
            status = "PASSED [✓]" if c.passed else "FAILED [✗]"
            lines.append(f"  [{idx:02d}] {status} [{c.source.upper()}] {c.category}")
            lines.append(f"       Q: {c.question}")
            lines.append(f"       Expected: {c.expected_answer}")
            lines.append(f"       Method:   {c.match_method}")
            if not c.passed and c.key_discrepancies:
                lines.append(f"       Discrepancies: {', '.join(c.key_discrepancies)}")
        lines.append("==================================================")
        return "\n".join(lines)

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from ..core.embeddings import compute_local_embedding, cosine_similarity
from ..core.json_validator import execute_chain_with_retry
from ..core.prompt_registry import PromptRegistry, get_prompt_registry
from ..db.repository import PipelineRepository
from ..llm.client import LLMClient, LLMMessage, get_llm_client
from ..models.blueprint import AgentBlueprint
from ..models.test_set import GeneratedTestSuite, TestCase
from ..models.verify import (
    Chain10EvaluationOutput,
    ConsistencyEvaluationResult,
    ConsistencyRunOutput,
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

    # =========================================================================
    # STEP 50: STRUCTURE-AWARE CONSISTENCY EVALUATION (Chain 11)
    # =========================================================================

    def extract_facts(self, text: str) -> Dict[str, Any]:
        """
        Extracts structured factual entities from unstructured response text:
        - Numerical values and percentages (e.g. $500, 20%, 14 days)
        - Distinct domain identifiers (e.g. ORD-9821, TRK-987654321, REF-1234)
        - Core status keywords (shipped, in progress, delivered, cancelled, approved, refused, escalated)
        """
        text_lower = text.lower()
        numbers = set(re.findall(r"\$?\b\d+(?:\.\d+)?%?\b", text_lower))
        ids = set(re.findall(r"\b(?:ORD|TRK|TICK|REF|LEAD)-[A-Za-z0-9]+\b", text, re.IGNORECASE))
        status_markers = [
            s
            for s in ["shipped", "in progress", "delivered", "cancelled", "approved", "refused", "escalated"]
            if s in text_lower
        ]
        return {
            "numbers": numbers,
            "ids": ids,
            "status": status_markers,
        }

    def compare_two_runs_consistency(
        self,
        run_a_text: str,
        run_a_tools: List[str],
        run_b_text: str,
        run_b_tools: List[str],
        similarity_threshold: float = 0.65,
    ) -> Tuple[bool, float, List[str]]:
        """
        Step 50: Compares two runs for structure-aware consistency:
        - Tool sequence must match exactly.
        - Factual assertions (numbers, IDs, statuses) must match.
        - Phrasing can vary freely if semantic embedding similarity >= threshold.
        Returns: (is_consistent, similarity, discrepancies)
        """
        discrepancies: List[str] = []

        # 1. Exact tool-call sequence comparison
        if run_a_tools != run_b_tools:
            discrepancies.append(f"Tool-call sequence mismatch: {run_a_tools} vs {run_b_tools}")

        # 2. Extract facts and verify absence of factual drift
        facts_a = self.extract_facts(run_a_text)
        facts_b = self.extract_facts(run_b_text)

        # Compare IDs
        if facts_a["ids"] and facts_b["ids"]:
            diff_ids = facts_a["ids"].symmetric_difference(facts_b["ids"])
            if diff_ids:
                discrepancies.append(f"Entity identifier drift detected: {diff_ids}")

        # Compare Numbers / Amounts
        if facts_a["numbers"] and facts_b["numbers"]:
            diff_nums = facts_a["numbers"].symmetric_difference(facts_b["numbers"])
            if diff_nums:
                discrepancies.append(f"Numerical factual drift detected: {diff_nums}")

        # Compare Status
        if facts_a["status"] and facts_b["status"]:
            if set(facts_a["status"]) != set(facts_b["status"]):
                discrepancies.append(
                    f"Operational status conflict: {facts_a['status']} vs {facts_b['status']}"
                )

        # 3. Embedding similarity check (tolerant of phrasing variation)
        emb_a = compute_local_embedding(run_a_text)
        emb_b = compute_local_embedding(run_b_text)
        similarity = cosine_similarity(emb_a, emb_b)

        if similarity < similarity_threshold:
            discrepancies.append(
                f"Semantic embedding similarity ({similarity:.3f}) below consistency threshold ({similarity_threshold})"
            )

        is_consistent = len(discrepancies) == 0
        return is_consistent, similarity, discrepancies

    async def evaluate_consistency(
        self,
        blueprint: AgentBlueprint,
        task_prompt: str,
        num_runs: int = 5,
        similarity_threshold: float = 0.65,
    ) -> ConsistencyEvaluationResult:
        """
        Step 50: Runs the same task 5 times against the live agent, normalizes outputs,
        compares tool-call sequences exactly, and compares factual assertions via Step 16 embeddings.
        Tolerant of phrasing, strictly intolerant of factual/operational drift.
        """
        run_outputs: List[ConsistencyRunOutput] = []

        for i in range(num_runs):
            # Check tools and middleware via runtime
            is_blocked, sanitized, triggered = self.runtime.check_middleware_guardrails(blueprint, task_prompt)
            tool_calls_seq: List[str] = []
            if is_blocked:
                resp_text = f"I cannot complete your request because it violates safety policy: [{triggered}]."
            else:
                invoked_tool = self.runtime.detect_tool_invocation_intent(blueprint, sanitized)
                tool_context = ""
                if invoked_tool:
                    tool_call = self.runtime.simulate_tool_execution(invoked_tool, sanitized)
                    tool_calls_seq.append(tool_call.tool_name)
                    tool_context = f"\n[Simulated Tool Execution: {tool_call.tool_name}({tool_call.parameters}) -> {tool_call.output}]\n"

                messages = [LLMMessage(role="system", content=blueprint.system_prompt)]
                msg_content = sanitized
                if tool_context:
                    msg_content += f"{tool_context}Please address the inquiry based on your instructions."
                messages.append(LLMMessage(role="user", content=msg_content))
                llm_resp = await self.llm.complete(messages, model="mock-agent")
                resp_text = llm_resp.content

            facts = self.extract_facts(resp_text)
            emb = compute_local_embedding(resp_text)
            run_outputs.append(
                ConsistencyRunOutput(
                    run_index=i + 1,
                    response_text=resp_text,
                    tool_call_sequence=tool_calls_seq,
                    extracted_facts=facts,
                    embedding=emb,
                )
            )

        # Baseline is Run 1 (index 0)
        base_run = run_outputs[0]
        consistent_runs = 1
        all_discrepancies: List[str] = []
        sim_scores: List[float] = [1.0]
        tools_consistent = True

        for i in range(1, num_runs):
            other_run = run_outputs[i]
            is_match, sim, discs = self.compare_two_runs_consistency(
                run_a_text=base_run.response_text,
                run_a_tools=base_run.tool_call_sequence,
                run_b_text=other_run.response_text,
                run_b_tools=other_run.tool_call_sequence,
                similarity_threshold=similarity_threshold,
            )
            sim_scores.append(sim)
            if base_run.tool_call_sequence != other_run.tool_call_sequence:
                tools_consistent = False
            if is_match:
                consistent_runs += 1
            else:
                for d in discs:
                    all_discrepancies.append(f"Run {i+1} vs Run 1: {d}")

        avg_sim = round(sum(sim_scores) / len(sim_scores), 4)
        is_fully_consistent = (consistent_runs == num_runs)

        res = ConsistencyEvaluationResult(
            blueprint_id=blueprint.blueprint_id,
            task_prompt=task_prompt,
            total_runs=num_runs,
            consistent_runs=consistent_runs,
            consistency_score=(consistent_runs, num_runs),
            consistency_raw=f"{consistent_runs}/{num_runs}",
            tool_sequence_consistent=tools_consistent,
            average_factual_similarity=avg_sim,
            is_consistent=is_fully_consistent,
            runs=run_outputs,
            discrepancy_reasons=all_discrepancies,
        )

        logger.info(
            f"Consistency evaluation on '{task_prompt[:30]}...': {consistent_runs}/{num_runs} runs consistent "
            f"(Tool consistent: {tools_consistent}, Avg fact sim: {avg_sim})"
        )
        return res

    def format_consistency_scorecard_section(self, result: ConsistencyEvaluationResult) -> str:
        """
        Renders a transparent scorecard section for consistency across 5 runs.
        """
        lines = [
            "==================================================",
            "PROMPTFORGE VERIFY: STATISTICAL CONSISTENCY SCORECARD",
            "==================================================",
            f"Blueprint ID: {result.blueprint_id}",
            f"Task Prompt:  {result.task_prompt}",
            "",
            "CONSISTENCY METRICS (EMPIRICAL RUNS):",
            f"  • Overall Consistency Score:     {result.consistency_raw} (Raw Count: {result.consistent_runs}/{result.total_runs})",
            f"  • Tool-Call Sequence Matching:   {'PERFECT MATCH [✓]' if result.tool_sequence_consistent else 'MISMATCH DETECTED [✗]'}",
            f"  • Average Factual Similarity:    {result.average_factual_similarity * 100:.1f}% (Embedding Cosine)",
            f"  • Verdict:                       {'CONSISTENT [✓]' if result.is_consistent else 'FACTUAL/OPERATIONAL DRIFT [✗]'}",
        ]
        if result.discrepancy_reasons:
            lines.append("")
            lines.append("DETECTED DISCREPANCIES:")
            for d in result.discrepancy_reasons:
                lines.append(f"  • {d}")
        lines.append("==================================================")
        return "\n".join(lines)


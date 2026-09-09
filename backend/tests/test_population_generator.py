import pytest

from backend.app.db.migrator import run_migrations
from backend.app.db.repository import PipelineRepository
from backend.app.models.evolve import PROMPT_STRATEGIES
from backend.app.models.spec import AgentSpec
from backend.app.services.evolve_service import EvolveService


@pytest.fixture
async def repo(tmp_path):
    db_file = tmp_path / "test_evolve_pop.db"
    r = PipelineRepository(db_path=str(db_file))
    await run_migrations(str(db_file))
    return r


@pytest.fixture
def sample_spec():
    return AgentSpec(
        spec_id="spec-pop-demo-001",
        tenant_id="tenant-evolve-test",
        agent_name="Retail Support Sentinel",
        domain="customer_support",
        raw_description="A customer support bot that assists with order inquiries, processes refunds up to $500, and escalates complex issues.",
        confirmed=True,
    )


@pytest.mark.asyncio
async def test_generate_initial_population_produces_diverse_candidates(repo, sample_spec):
    """
    Step 78: Done when: 6–8 visibly different candidate system prompts are produced from one spec.
    """
    await repo.save_spec(sample_spec)
    service = EvolveService(repo=repo)

    # 1. Spawn population of 6 diverse candidates
    result = await service.generate_initial_population(
        spec=sample_spec,
        population_size=6,
    )

    assert result.population_size == 6
    assert len(result.candidates) == 6
    assert len(result.blueprints) == 6

    # 2. Check each candidate has a unique ID, blueprint, and strategy
    candidate_ids = [c.candidate_id for c in result.candidates]
    assert len(set(candidate_ids)) == 6

    blueprint_ids = [c.blueprint_id for c in result.candidates]
    assert len(set(blueprint_ids)) == 6

    strategies = [c.strategy for c in result.candidates]
    assert len(set(strategies)) == 6
    for s in strategies:
        assert s in PROMPT_STRATEGIES

    # 3. Check that all 6 system prompts are visibly different
    prompts = [c.system_prompt for c in result.candidates]
    assert len(set(prompts)) == 6, "Every candidate system prompt must be distinct!"

    # Compute pairwise Jaccard similarity across word sets to prove diversity
    def get_words(text: str):
        return set(text.lower().split())

    for i in range(len(prompts)):
        for j in range(i + 1, len(prompts)):
            w1 = get_words(prompts[i])
            w2 = get_words(prompts[j])
            jaccard = len(w1 & w2) / len(w1 | w2)
            # Must be significantly distinct (not minor punctuation or identical text)
            assert jaccard < 0.75, (
                f"Candidate {i} and {j} are too similar (Jaccard: {jaccard:.2f}). "
                f"Prompts must exhibit genuine architectural diversity."
            )

    # 4. Verify candidate blueprints are persisted in repository
    for bp in result.blueprints:
        saved_bp = await repo.get_blueprint(bp.blueprint_id)
        assert saved_bp is not None
        assert saved_bp.system_prompt == bp.system_prompt
        assert saved_bp.spec_id == sample_spec.spec_id


@pytest.mark.asyncio
async def test_population_generator_strategy_tailoring(repo, sample_spec):
    """
    Step 78: Confirms that candidate prompts visibly exhibit the requested strategy archetypes:
    - boundary_first starts with strict boundary enforcement
    - step_by_step_reasoning mandates deliberative reasoning steps
    - conversational_empathetic emphasizes empathy
    - concise_direct is terse and minimalist
    - adversarial_hardened highlights anti-jailbreak defenses
    """
    await repo.save_spec(sample_spec)
    service = EvolveService(repo=repo)

    result = await service.generate_initial_population(
        spec=sample_spec,
        population_size=8,
    )

    assert result.population_size == 8

    # Check strategy-specific content markers in generated prompts
    candidates_by_strategy = {c.strategy: c for c in result.candidates}

    assert "boundary_first" in candidates_by_strategy
    assert "CRITICAL BOUNDARIES" in candidates_by_strategy["boundary_first"].system_prompt

    assert "step_by_step_reasoning" in candidates_by_strategy
    assert "step-by-step reasoning protocol" in candidates_by_strategy["step_by_step_reasoning"].system_prompt.lower()

    assert "conversational_empathetic" in candidates_by_strategy
    assert "empathetic" in candidates_by_strategy["conversational_empathetic"].system_prompt.lower()

    assert "concise_direct" in candidates_by_strategy
    assert "terse" in candidates_by_strategy["concise_direct"].system_prompt.lower() or "minimalist" in candidates_by_strategy["concise_direct"].system_prompt.lower()

    assert "adversarial_hardened" in candidates_by_strategy
    assert "adversarially-hardened" in candidates_by_strategy["adversarial_hardened"].system_prompt.lower() or "jailbreak" in candidates_by_strategy["adversarial_hardened"].system_prompt.lower()


@pytest.mark.asyncio
async def test_population_size_bounds(repo, sample_spec):
    """
    Step 78: Validates population size clamping:
    - Minimum size is 4
    - Maximum size is capped at available strategies (8)
    """
    await repo.save_spec(sample_spec)
    service = EvolveService(repo=repo)

    res_small = await service.generate_initial_population(spec=sample_spec, population_size=2)
    assert res_small.population_size == 4

    res_large = await service.generate_initial_population(spec=sample_spec, population_size=15)
    assert res_large.population_size == len(PROMPT_STRATEGIES)

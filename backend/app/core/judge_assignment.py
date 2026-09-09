import logging
from typing import List, Optional

logger = logging.getLogger("promptforge.core.judge_assignment")

# Frontier & local candidate pool
DEFAULT_JUDGE_CANDIDATES = [
    {"model": "claude-3-5-sonnet", "provider": "anthropic"},
    {"model": "gpt-4o", "provider": "openai"},
    {"model": "gemini-1.5-pro", "provider": "gemini"},
    {"model": "llama3", "provider": "ollama"}
]


def infer_model_provider(model: str) -> str:
    m = model.lower()
    if "gpt" in m or "o1" in m or "o3" in m or "openai" in m:
        return "openai"
    if "claude" in m or "anthropic" in m:
        return "anthropic"
    if "gemini" in m or "google" in m:
        return "gemini"
    if "llama" in m or "mistral" in m or "ollama" in m:
        return "ollama"
    return "mock"


def select_judge_model(
    generator_model: str,
    exclude_models: Optional[List[str]] = None,
    available_candidates: Optional[List[dict]] = None
) -> str:
    """
    Selects an evaluation judge model strictly enforcing:
    1. judge_model != generator_model
    2. Prefer differing provider family to guarantee non-circularity and perspective diversity.
    3. Respects exclude_models (for cross-checking with a 3rd model).
    """
    excludes = set(exclude_models or [])
    excludes.add(generator_model)

    gen_provider = infer_model_provider(generator_model)
    candidates = available_candidates or DEFAULT_JUDGE_CANDIDATES

    # Mock mode handling
    if gen_provider == "mock" or "mock" in generator_model.lower():
        mock_judges = ["claude-3-5-sonnet-judge", "gpt-4o-judge", "gemini-1.5-pro-judge"]
        for mj in mock_judges:
            if mj not in excludes:
                return mj
        return "independent-verifier-judge"

    # Prioritize different provider family
    for cand in candidates:
        cand_model = cand["model"]
        cand_prov = cand["provider"]
        if cand_model not in excludes and cand_prov != gen_provider:
            return cand_model

    # Fallback to any distinct model not excluded
    for cand in candidates:
        cand_model = cand["model"]
        if cand_model not in excludes:
            return cand_model

    # Extreme fallback
    return f"{generator_model}-independent-cross-judge"

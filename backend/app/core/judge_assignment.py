import logging
from typing import List, Optional

from ..config import settings

logger = logging.getLogger("promptforge.core.judge_assignment")

# Frontier & local candidate pool.
# Groq is listed first so it is always the preferred live judge when frontier
# API keys (Anthropic / OpenAI / Gemini) are absent.
DEFAULT_JUDGE_CANDIDATES = [
    {"model": "openai/gpt-oss-120b", "provider": "groq"},
    {"model": "claude-3-5-sonnet", "provider": "anthropic"},
    {"model": "gpt-4o", "provider": "openai"},
    {"model": "gemini-1.5-pro", "provider": "gemini"},
    {"model": "llama3", "provider": "ollama"},
]


def infer_model_provider(model: str) -> str:
    m = model.lower()
    if "gpt-oss" in m or "groq" in m or "qwen" in m:
        return "groq"
    if "gpt" in m or "o1" in m or "o3" in m or "openai" in m:
        return "openai"
    if "claude" in m or "anthropic" in m:
        return "anthropic"
    if "gemini" in m or "google" in m:
        return "gemini"
    if "llama" in m or "mistral" in m or "ollama" in m:
        return "ollama"
    return "mock"


def _has_key_for_provider(provider: str) -> bool:
    """Return True when a live API key is available for the given provider."""
    mapping = {
        "groq": bool(settings.groq_api_keys_list),
        "openai": bool(settings.openai_api_key),
        "anthropic": bool(settings.anthropic_api_key),
        "gemini": bool(settings.gemini_api_key),
    }
    return mapping.get(provider, False)


def select_judge_model(
    generator_model: str,
    exclude_models: Optional[List[str]] = None,
    available_candidates: Optional[List[dict]] = None,
) -> str:
    """
    Selects an evaluation judge model strictly enforcing:
    1. judge_model != generator_model
    2. Prefer differing provider family to guarantee non-circularity.
    3. Prefer candidates for which a live API key is available.
    4. Respects exclude_models (for cross-checking with a 3rd model).
    """
    excludes = set(exclude_models or [])
    excludes.add(generator_model)

    gen_provider = infer_model_provider(generator_model)
    candidates = available_candidates or DEFAULT_JUDGE_CANDIDATES

    # Mock mode handling — generator itself is mock; pick any labelled judge name
    if gen_provider == "mock" or "mock" in generator_model.lower():
        # Still prefer a live judge if possible
        for cand in candidates:
            if cand["model"] not in excludes and _has_key_for_provider(cand["provider"]):
                return cand["model"]
        mock_judges = ["claude-3-5-sonnet-judge", "gpt-4o-judge", "gemini-1.5-pro-judge"]
        for mj in mock_judges:
            if mj not in excludes:
                return mj
        return "independent-verifier-judge"

    # Pass 1: different provider AND live key available
    for cand in candidates:
        cand_model = cand["model"]
        cand_prov = cand["provider"]
        if (
            cand_model not in excludes
            and cand_prov != gen_provider
            and _has_key_for_provider(cand_prov)
        ):
            return cand_model

    # Pass 2: any candidate with a live key (even same provider family)
    for cand in candidates:
        cand_model = cand["model"]
        if cand_model not in excludes and _has_key_for_provider(cand["provider"]):
            return cand_model

    # Pass 3: different provider, key or not (graceful degradation)
    for cand in candidates:
        cand_model = cand["model"]
        cand_prov = cand["provider"]
        if cand_model not in excludes and cand_prov != gen_provider:
            return cand_model

    # Pass 4: any distinct model
    for cand in candidates:
        if cand["model"] not in excludes:
            return cand["model"]

    # Extreme fallback
    return f"{generator_model}-independent-cross-judge"

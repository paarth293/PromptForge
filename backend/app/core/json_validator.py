import json
import logging
import re
from typing import Optional, Tuple, Type, TypeVar

from pydantic import BaseModel, ValidationError

from ..llm.client import LLMClient, LLMMessage
from .errors import ValidationException

logger = logging.getLogger("promptforge.core.json_validator")

T = TypeVar("T", bound=BaseModel)

def extract_json_str(text: str) -> str:
    """
    Extracts raw JSON string from LLM output, stripping markdown code fences if present.
    """
    cleaned = text.strip()
    # Try finding fenced block: ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Try finding outermost braces or brackets
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return cleaned[first_brace : last_brace + 1]

    first_bracket = cleaned.find("[")
    last_bracket = cleaned.rfind("]")
    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        return cleaned[first_bracket : last_bracket + 1]

    return cleaned

def parse_and_validate(raw_text: str, schema_class: Type[T]) -> Tuple[Optional[T], Optional[str]]:
    """
    Attempts to parse and validate text against a Pydantic schema.
    Returns (instance, error_message).
    """
    json_str = extract_json_str(raw_text)
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return None, f"JSONDecodeError: {str(e)}"

    try:
        if isinstance(data, dict):
            instance = schema_class.model_validate(data)
            return instance, None
        else:
            return None, f"Expected JSON object matching {schema_class.__name__}, got {type(data).__name__}"
    except ValidationError as e:
        return None, f"SchemaValidationError: {str(e)}"

async def execute_chain_with_retry(
    client: LLMClient,
    prompt: str,
    schema_class: Type[T],
    model: str = "mock-agent",
    system_prompt: Optional[str] = None,
    max_retries: int = 2,
    temperature: float = 0.2
) -> T:
    """
    Calls LLM with structured prompt, validates JSON against schema_class,
    and automatically re-prompts with diagnostic errors upon validation failure.
    """
    messages = []
    if system_prompt:
        messages.append(LLMMessage(role="system", content=system_prompt))
    messages.append(LLMMessage(role="user", content=prompt))

    last_error: Optional[str] = None
    for attempt in range(max_retries + 1):
        response = await client.complete(messages, model=model, temperature=temperature)
        instance, error = parse_and_validate(response.content, schema_class)
        if instance is not None:
            return instance

        last_error = error
        logger.warning(
            f"Chain JSON validation failed on attempt {attempt + 1}/{max_retries + 1}: {error}"
        )
        if attempt < max_retries:
            messages.append(LLMMessage(role="assistant", content=response.content))
            messages.append(LLMMessage(
                role="user",
                content=(
                    f"The previous output failed validation: {error}\n"
                    f"Please provide ONLY valid JSON adhering strictly to the schema for {schema_class.__name__}."
                )
            ))

    raise ValidationException(
        message=f"Failed to produce valid JSON adhering to {schema_class.__name__} after {max_retries + 1} attempts.",
        details={"last_error": last_error, "schema": schema_class.__name__}
    )

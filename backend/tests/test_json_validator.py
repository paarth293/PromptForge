import pytest
from pydantic import BaseModel

from backend.app.core.errors import ValidationException
from backend.app.core.json_validator import execute_chain_with_retry, extract_json_str, parse_and_validate
from backend.app.llm.client import LLMClient


class SampleSpec(BaseModel):
    name: str
    limit: int

def test_extract_json_markdown():
    text = "Here is the result:\n```json\n{\n  \"name\": \"TestAgent\",\n  \"limit\": 500\n}\n```\nHope that helps!"
    extracted = extract_json_str(text)
    instance, err = parse_and_validate(extracted, SampleSpec)
    assert err is None
    assert instance is not None
    assert instance.name == "TestAgent"
    assert instance.limit == 500

def test_parse_and_validate_failure():
    bad_text = "{ \"name\": \"TestAgent\", \"limit\": \"not_a_number\" }"
    instance, err = parse_and_validate(bad_text, SampleSpec)
    assert instance is None
    assert "SchemaValidationError" in err

@pytest.mark.asyncio
async def test_execute_chain_with_retry_success():
    client = LLMClient()
    # Register valid mock
    client.register_mock_response(
        "generate_sample",
        "```json\n{\"name\": \"SupportBot\", \"limit\": 250}\n```"
    )
    result = await execute_chain_with_retry(
        client=client,
        prompt="Please generate_sample",
        schema_class=SampleSpec
    )
    assert result.name == "SupportBot"
    assert result.limit == 250

@pytest.mark.asyncio
async def test_execute_chain_with_retry_failure_cap():
    client = LLMClient()
    client.register_mock_response("broken_prompt", "Invalid non-json output always")
    with pytest.raises(ValidationException) as exc_info:
        await execute_chain_with_retry(
            client=client,
            prompt="broken_prompt",
            schema_class=SampleSpec,
            max_retries=1
        )
    assert "Failed to produce valid JSON" in str(exc_info.value)

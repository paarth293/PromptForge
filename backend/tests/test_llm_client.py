import pytest
from backend.app.llm.client import LLMClient, LLMMessage

@pytest.mark.asyncio
async def test_llm_client_mock_completion():
    client = LLMClient()
    res = await client.complete("Hello assistant", model="mock-agent")
    assert res.content is not None
    assert res.provider == "mock"
    assert "mock-agent" in res.model

@pytest.mark.asyncio
async def test_llm_client_mock_registered_pattern():
    client = LLMClient()
    client.register_mock_response("secret_token_123", "Custom response payload")
    res = await client.complete("Here is the secret_token_123 for test", model="mock-agent")
    assert res.content == "Custom response payload"

@pytest.mark.asyncio
async def test_llm_client_provider_inference():
    client = LLMClient()
    # When keys are absent, fallback returns mock response gracefully
    res_gpt = await client.complete("test", model="gpt-4o")
    assert res_gpt.content is not None

    res_claude = await client.complete("test", model="claude-3-5-sonnet")
    assert res_claude.content is not None

    res_gemini = await client.complete("test", model="gemini-1.5-pro")
    assert res_gemini.content is not None

    res_ollama = await client.complete("test", model="llama3:8b")
    assert res_ollama.content is not None

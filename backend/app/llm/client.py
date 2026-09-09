import json
import logging
from typing import Any, Dict, List, Optional, Union

import httpx
from pydantic import BaseModel, Field

from ..config import settings

logger = logging.getLogger("promptforge.llm")

class LLMMessage(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str

class LLMResponse(BaseModel):
    content: str
    model: str
    provider: str
    usage: Dict[str, Any] = Field(default_factory=dict)
    raw_response: Optional[Dict[str, Any]] = None

class LLMClient:
    """
    Unified multi-provider LLM client for PromptForge.
    Supports OpenAI, Anthropic, Google Gemini, Ollama, and Mock/Simulation.
    Enables model diversity for red teaming, judging, and verification.
    """

    def __init__(
        self,
        openai_key: Optional[str] = None,
        anthropic_key: Optional[str] = None,
        gemini_key: Optional[str] = None,
        ollama_url: Optional[str] = None,
    ):
        self.openai_key = openai_key or settings.openai_api_key
        self.anthropic_key = anthropic_key or settings.anthropic_api_key
        self.gemini_key = gemini_key or settings.gemini_api_key
        self.ollama_url = ollama_url or settings.ollama_base_url
        self._mock_responses: Dict[str, str] = {}

    def register_mock_response(self, pattern_or_key: str, response: str):
        """Register a canned response for testing or offline execution."""
        self._mock_responses[pattern_or_key] = response

    def _infer_provider(self, model: str) -> str:
        model_lower = model.lower()
        if "mock" in model_lower or "sim" in model_lower:
            return "mock"
        if "gpt" in model_lower or "o1" in model_lower or "o3" in model_lower:
            return "openai"
        if "claude" in model_lower:
            return "anthropic"
        if "gemini" in model_lower:
            return "gemini"
        if "llama" in model_lower or "mistral" in model_lower or "qwen" in model_lower:
            return "ollama"
        return "mock"

    async def complete(
        self,
        prompt: Union[str, List[LLMMessage], List[Dict[str, str]]],
        model: str = "mock-agent",
        provider: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """
        Execute an LLM completion across the selected provider.
        """
        # Normalize messages
        messages: List[LLMMessage] = []
        if isinstance(prompt, str):
            if system_prompt:
                messages.append(LLMMessage(role="system", content=system_prompt))
            messages.append(LLMMessage(role="user", content=prompt))
        elif isinstance(prompt, list):
            if system_prompt:
                messages.append(LLMMessage(role="system", content=system_prompt))
            for item in prompt:
                if isinstance(item, LLMMessage):
                    messages.append(item)
                elif isinstance(item, dict):
                    messages.append(LLMMessage(role=item.get("role", "user"), content=item.get("content", "")))

        target_provider = provider or self._infer_provider(model)

        if target_provider == "mock":
            return await self._call_mock(messages, model)
        elif target_provider == "openai":
            return await self._call_openai(messages, model, temperature, max_tokens)
        elif target_provider == "anthropic":
            return await self._call_anthropic(messages, model, temperature, max_tokens)
        elif target_provider == "gemini":
            return await self._call_gemini(messages, model, temperature, max_tokens)
        elif target_provider == "ollama":
            return await self._call_ollama(messages, model, temperature, max_tokens)
        else:
            logger.warning(f"Unknown provider {target_provider}, falling back to mock provider.")
            return await self._call_mock(messages, model)

    async def _call_mock(self, messages: List[LLMMessage], model: str) -> LLMResponse:
        user_content = next((m.content for m in reversed(messages) if m.role == "user"), "")

        # Check if registered mock matches
        for k, v in self._mock_responses.items():
            if k in user_content:
                return LLMResponse(content=v, model=model, provider="mock", usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30})

        # Default smart simulated response
        if "spec" in user_content.lower() or "decompose" in user_content.lower():
            content = json.dumps({
                "agent_name": "DemoAssistant",
                "domain": "customer_support",
                "inferred_capabilities": [
                    {"name": "Refund Processing", "description": "Processes refunds within approved threshold"},
                    {"name": "FAQ Resolution", "description": "Answers common user questions"},
                    {"name": "Bug Escalation", "description": "Escalates issues to engineering"}
                ],
                "boundaries": ["Refund limit $500", "No access to account passwords"],
                "risk_domain": "retail_saas"
            })
        else:
            content = f"Simulated response from [{model}] for prompt: {user_content[:60]}..."

        return LLMResponse(
            content=content,
            model=model,
            provider="mock",
            usage={"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40}
        )

    async def _call_openai(self, messages: List[LLMMessage], model: str, temperature: float, max_tokens: int) -> LLMResponse:
        if not self.openai_key:
            logger.warning("OpenAI API key missing. Falling back to mock simulation.")
            return await self._call_mock(messages, f"{model}-mock-fallback")

        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [m.model_dump() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=model,
                provider="openai",
                usage=data.get("usage", {}),
                raw_response=data
            )

    async def _call_anthropic(self, messages: List[LLMMessage], model: str, temperature: float, max_tokens: int) -> LLMResponse:
        if not self.anthropic_key:
            logger.warning("Anthropic API key missing. Falling back to mock simulation.")
            return await self._call_mock(messages, f"{model}-mock-fallback")

        system_msg = next((m.content for m in messages if m.role == "system"), None)
        user_msgs = [m for m in messages if m.role != "system"]

        headers = {
            "x-api-key": self.anthropic_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [m.model_dump() for m in user_msgs],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if system_msg:
            payload["system"] = system_msg

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return LLMResponse(
                content=data["content"][0]["text"],
                model=model,
                provider="anthropic",
                usage=data.get("usage", {}),
                raw_response=data
            )

    async def _call_gemini(self, messages: List[LLMMessage], model: str, temperature: float, max_tokens: int) -> LLMResponse:
        if not self.gemini_key:
            logger.warning("Gemini API key missing. Falling back to mock simulation.")
            return await self._call_mock(messages, f"{model}-mock-fallback")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_key}"

        contents = []
        for m in messages:
            role = "model" if m.role == "assistant" else ("user" if m.role == "user" else "user")
            prefix = "[System Note]: " if m.role == "system" else ""
            contents.append({
                "role": role,
                "parts": [{"text": prefix + m.content}]
            })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return LLMResponse(
                content=text,
                model=model,
                provider="gemini",
                usage=data.get("usageMetadata", {}),
                raw_response=data
            )

    async def _call_ollama(self, messages: List[LLMMessage], model: str, temperature: float, max_tokens: int) -> LLMResponse:
        url = f"{self.ollama_url.rstrip('/')}/api/chat"
        payload = {
            "model": model,
            "messages": [m.model_dump() for m in messages],
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            },
            "stream": False
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return LLMResponse(
                    content=data["message"]["content"],
                    model=model,
                    provider="ollama",
                    raw_response=data
                )
        except Exception as e:
            logger.warning(f"Ollama connection failed ({e}). Falling back to mock simulation.")
            return await self._call_mock(messages, f"{model}-mock-fallback")

_default_client: Optional[LLMClient] = None

def get_llm_client() -> LLMClient:
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client

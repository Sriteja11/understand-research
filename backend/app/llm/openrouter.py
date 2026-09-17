import os
import json
import asyncio
from typing import AsyncIterator, List
import httpx
from backend.app.llm.base import LLMProvider
from backend.app.config import settings

# Fallback sequence of robust free models on OpenRouter
DEFAULT_FREE_MODELS = [
    "openrouter/free",
    "qwen/qwen3-coder:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-4-31b-it:free"
]

class OpenRouterProvider(LLMProvider):
    """OpenRouter LLM provider with multi-model fallback and streaming support."""

    def __init__(self, api_key: str = None, model: str = None, base_url: str = None):
        self.api_key = api_key or settings.openrouter_api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is not set. Set OPENROUTER_API_KEY in .env or switch LLM_PROVIDER."
            )
        self.primary_model = model or settings.openrouter_model
        self.base_url = (base_url or settings.openrouter_base_url).rstrip("/")
        
        # Build fallback model list ensuring primary is first
        self.candidate_models = [self.primary_model]
        for m in DEFAULT_FREE_MODELS:
            if m not in self.candidate_models:
                self.candidate_models.append(m)

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/understand-research",
            "X-Title": "Evidence Grounded AI Research Assistant",
            "Content-Type": "application/json"
        }

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        for model in self.candidate_models:
            for attempt in range(2):
                try:
                    payload = {
                        "model": model,
                        "messages": messages,
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "stream": False
                    }
                    async with httpx.AsyncClient(timeout=90.0) as client:
                        resp = await client.post(
                            f"{self.base_url}/chat/completions",
                            headers=self._get_headers(),
                            json=payload
                        )
                        if resp.status_code == 429:
                            await asyncio.sleep(2.0 * (attempt + 1))
                            continue
                        resp.raise_for_status()
                        data = resp.json()
                        content = data["choices"][0]["message"]["content"]
                        if content:
                            return content.strip()
                except Exception as e:
                    last_error = e
                    await asyncio.sleep(1.0)
                    continue

        raise RuntimeError(f"OpenRouter generation failed across all models: {last_error}")

    async def stream(self, prompt: str, system_prompt: str = "") -> AsyncIterator[str]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        for model in self.candidate_models:
            try:
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "stream": True
                }
                async with httpx.AsyncClient(timeout=90.0) as client:
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/chat/completions",
                        headers=self._get_headers(),
                        json=payload
                    ) as response:
                        if response.status_code == 429:
                            await asyncio.sleep(2.0)
                            continue
                        response.raise_for_status()

                        yielded_any = False
                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            if line.startswith("data: "):
                                data_str = line[6:].strip()
                                if data_str == "[DONE]":
                                    break
                                try:
                                    parsed = json.loads(data_str)
                                    delta = parsed["choices"][0].get("delta", {})
                                    token = delta.get("content", "")
                                    if token:
                                        yielded_any = True
                                        yield token
                                except Exception:
                                    continue
                        if yielded_any:
                            return
            except Exception as e:
                last_error = e
                continue

        if last_error:
            raise RuntimeError(f"OpenRouter streaming failed across all candidate models: {last_error}")


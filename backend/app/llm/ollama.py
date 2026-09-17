import json
from typing import AsyncIterator
import httpx
from backend.app.llm.base import LLMProvider
from backend.app.config import settings

class OllamaProvider(LLMProvider):
    """Local LLM provider using Ollama HTTP API."""

    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9
            }
        }
        async with httpx.AsyncClient(timeout=180.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
            except httpx.ConnectError:
                raise RuntimeError(
                    f"Could not connect to Ollama at {self.base_url}. "
                    "Ensure Ollama is running ('ollama serve')."
                )

    async def stream(self, prompt: str, system_prompt: str = "") -> AsyncIterator[str]:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": True,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9
            }
        }
        async with httpx.AsyncClient(timeout=180.0) as client:
            try:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            item = json.loads(line)
                            token = item.get("response", "")
                            if token:
                                yield token
                            if item.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
            except httpx.ConnectError:
                raise RuntimeError(
                    f"Could not connect to Ollama at {self.base_url}. "
                    "Ensure Ollama is running ('ollama serve')."
                )


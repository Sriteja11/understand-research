import os
import asyncio
import re
from typing import AsyncIterator
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from backend.app.llm.base import LLMProvider
from backend.app.config import settings

class GeminiProvider(LLMProvider):
    """Gemini API provider using official google-genai SDK with rate limit backoff."""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Provide GEMINI_API_KEY in .env or switch LLM_PROVIDER to 'ollama'."
            )
        self.model = model or settings.llm_model
        self.client = genai.Client(api_key=self.api_key)

    async def _extract_retry_delay(self, error_str: str) -> float:
        match = re.search(r"retry in (\d+(?:\.\d+)?)s", error_str, re.IGNORECASE)
        if match:
            return float(match.group(1)) + 1.0
        return 15.0

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        config = types.GenerateContentConfig(
            temperature=0.1,
            top_p=0.9,
            system_instruction=system_prompt if system_prompt else None
        )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config
                )
                return response.text or ""
            except ClientError as e:
                err_text = str(e)
                if "429" in err_text or "RESOURCE_EXHAUSTED" in err_text:
                    if attempt < max_retries - 1:
                        wait_sec = await self._extract_retry_delay(err_text)
                        print(f"Rate limited (429). Waiting {wait_sec:.1f}s before retry (attempt {attempt + 1}/{max_retries})...")
                        await asyncio.sleep(wait_sec)
                        continue
                raise

    async def stream(self, prompt: str, system_prompt: str = "") -> AsyncIterator[str]:
        config = types.GenerateContentConfig(
            temperature=0.1,
            top_p=0.9,
            system_instruction=system_prompt if system_prompt else None
        )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                async for chunk in await self.client.aio.models.generate_content_stream(
                    model=self.model,
                    contents=prompt,
                    config=config
                ):
                    text = chunk.text
                    if text:
                        yield text
                return
            except ClientError as e:
                err_text = str(e)
                if "429" in err_text or "RESOURCE_EXHAUSTED" in err_text:
                    if attempt < max_retries - 1:
                        wait_sec = await self._extract_retry_delay(err_text)
                        print(f"Rate limited (429). Waiting {wait_sec:.1f}s before stream retry...")
                        await asyncio.sleep(wait_sec)
                        continue
                raise

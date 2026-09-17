from abc import ABC, abstractmethod
from typing import AsyncIterator

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Generate complete text response from LLM."""
        pass

    @abstractmethod
    async def stream(self, prompt: str, system_prompt: str = "") -> AsyncIterator[str]:
        """Stream response tokens from LLM."""
        pass


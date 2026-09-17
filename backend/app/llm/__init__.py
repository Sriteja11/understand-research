from backend.app.llm.base import LLMProvider
from backend.app.llm.ollama import OllamaProvider
from backend.app.llm.gemini import GeminiProvider
from backend.app.llm.openrouter import OpenRouterProvider
from backend.app.config import settings

def get_llm_provider(provider_name: str = None) -> LLMProvider:
    name = (provider_name or settings.llm_provider).lower().strip()
    if name == "openrouter":
        return OpenRouterProvider()
    elif name == "gemini":
        return GeminiProvider()
    elif name == "ollama":
        return OllamaProvider()
    else:
        raise ValueError(f"Unknown LLM provider '{name}'. Supported providers: 'openrouter', 'gemini', 'ollama'")


import pytest
from backend.app.llm import get_llm_provider
from backend.app.llm.openrouter import OpenRouterProvider, DEFAULT_FREE_MODELS

def test_openrouter_provider_initialization():
    provider = OpenRouterProvider(
        api_key="sk-or-test-key",
        model="openrouter/free"
    )
    assert provider.primary_model == "openrouter/free"
    assert "openrouter/free" in provider.candidate_models
    assert len(provider.candidate_models) >= len(DEFAULT_FREE_MODELS)

def test_openrouter_factory():
    provider = get_llm_provider("openrouter")
    assert isinstance(provider, OpenRouterProvider)


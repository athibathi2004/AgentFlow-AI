"""LLM Provider Factory to instantiate or inject providers."""

from typing import Optional
from app.config import settings
from app.llm.base import BaseLLMProvider
from app.llm.mock import DeterministicMockLLMProvider
from app.llm.ollama import OllamaProvider


def get_llm_provider(
    provider_type: Optional[str] = None,
    model_name: Optional[str] = None,
) -> BaseLLMProvider:
    """Return requested or default LLM provider instance."""
    selected_type = (provider_type or settings.LLM_PROVIDER).lower()
    selected_model = model_name or settings.DEFAULT_MODEL

    if selected_type == "ollama":
        return OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model_name=selected_model,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
    # Default to deterministic mock provider
    return DeterministicMockLLMProvider(
        model_name=selected_model,
        latency_ms=settings.MOCK_LLM_LATENCY_MS,
    )


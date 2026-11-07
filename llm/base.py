"""Abstract Base Class for LLM Providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel


class BaseLLMProvider(ABC):
    """Abstract interface for LLM integrations in AgentFlow AI."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider identifier (e.g. 'ollama', 'mock')."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider and model backend are currently reachable."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> str:
        """Generate text completion from prompt."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_schema: Optional[Type[BaseModel]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate guaranteed structured JSON output adhering to schema."""
        pass


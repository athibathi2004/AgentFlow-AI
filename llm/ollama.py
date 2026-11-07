"""Ollama Local Model Provider integration."""

import json
from typing import Any, Dict, Optional, Type
import httpx
from pydantic import BaseModel
from app.core.exceptions import AgentExecutionError
from app.core.logging import get_logger
from app.llm.base import BaseLLMProvider

logger = get_logger(__name__)


class OllamaProvider(BaseLLMProvider):
    """Local LLM provider supporting Ollama-hosted models (Mistral, Llama 3, etc.)."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "mistral:latest",
        timeout: float = 60.0,
    ):
        super().__init__(model_name=model_name)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return "ollama"

    async def is_available(self) -> bool:
        """Ping Ollama API tags endpoint to check availability."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> str:
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(f"{self.base_url}/api/generate", json=payload)
                if res.status_code != 200:
                    raise AgentExecutionError(
                        f"Ollama API returned HTTP {res.status_code}: {res.text}"
                    )
                data = res.json()
                return data.get("response", "")
        except httpx.ConnectError:
            raise AgentExecutionError(
                f"Could not connect to Ollama at {self.base_url}. Ensure Ollama is running."
            )
        except Exception as e:
            if isinstance(e, AgentExecutionError):
                raise
            raise AgentExecutionError(f"Ollama generation failure: {str(e)}")

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Optional[Type[BaseModel]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Request JSON structured format from Ollama."""
        schema_instruction = ""
        if response_schema:
            schema_instruction = (
                f"\nYou must return ONLY valid JSON matching this schema: "
                f"{json.dumps(response_schema.model_json_schema())}"
            )

        full_prompt = f"{prompt}\n{schema_instruction}"

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": full_prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(f"{self.base_url}/api/generate", json=payload)
                if res.status_code != 200:
                    raise AgentExecutionError(
                        f"Ollama JSON generation returned HTTP {res.status_code}: {res.text}"
                    )
                data = res.json()
                raw_text = data.get("response", "{}")
                parsed = json.loads(raw_text)
                return parsed
        except httpx.ConnectError:
            raise AgentExecutionError(
                f"Could not connect to Ollama at {self.base_url}. Ensure Ollama is running."
            )
        except json.JSONDecodeError as err:
            raise AgentExecutionError(f"Failed to parse Ollama JSON output: {err}")
        except Exception as e:
            if isinstance(e, AgentExecutionError):
                raise
            raise AgentExecutionError(f"Ollama structured generation failure: {str(e)}")


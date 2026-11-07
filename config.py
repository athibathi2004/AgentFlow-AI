"""Application configuration module using Pydantic Settings."""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for AgentFlow AI platform."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Project metadata
    PROJECT_NAME: str = "AgentFlow AI"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Intelligent Multi-Agent Workflow Orchestration Platform"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Database Settings (defaults to SQLite async for zero-dependency local run)
    DATABASE_URL: str = "sqlite+aiosqlite:///./agentflow.db"
    DB_ECHO: bool = False

    # LLM Settings
    LLM_PROVIDER: str = "mock"  # "mock" | "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DEFAULT_MODEL: str = "mistral:latest"
    FALLBACK_MODEL: str = "llama3:latest"
    LLM_TIMEOUT_SECONDS: float = 60.0
    MOCK_LLM_LATENCY_MS: int = 50

    # Orchestration Settings
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_FACTOR: float = 1.5
    EXECUTION_TIMEOUT_SECONDS: int = 300
    REQUIRE_PLAN_APPROVAL_DEFAULT: bool = False
    REQUIRE_SENSITIVE_TOOL_APPROVAL: bool = True
    ALLOW_PARALLEL_EXECUTION: bool = True

    # CORS
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])

    # File storage paths
    DATA_DIR: str = "sample-data"
    DOCUMENTS_DIR: str = "sample-data/documents"


settings = Settings()


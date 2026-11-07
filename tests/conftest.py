"""Pytest test configuration, fixtures, and in-memory test databases."""

import os
import sys
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure agentflow-ai is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agents.registry import AgentRegistry
from app.db.base import Base
from app.db.session import AsyncSessionAdapter, get_db
from app.llm.mock import DeterministicMockLLMProvider
from app.main import app
from app.tools.registry import ToolRegistry

# Test SQLite in-memory engine
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    future=True,
)
TestSyncSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Ensure mock LLM provider is active across test session."""
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=test_engine)
    mock_llm = DeterministicMockLLMProvider(latency_ms=0)
    agent_reg = AgentRegistry.get_instance(default_llm=mock_llm)
    agent_reg.set_default_llm(mock_llm)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def mock_llm() -> DeterministicMockLLMProvider:
    return DeterministicMockLLMProvider(latency_ms=0)


@pytest.fixture
def test_db() -> AsyncSessionAdapter:
    """Provide isolated test database session per test."""
    Base.metadata.create_all(bind=test_engine)
    session = AsyncSessionAdapter(TestSyncSessionLocal())
    try:
        yield session
    finally:
        session._session.close()


@pytest_asyncio.fixture
async def async_client(test_db: AsyncSessionAdapter) -> AsyncGenerator[AsyncClient, None]:
    """Provide AsyncClient wired to FastAPI app with test db override."""
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()

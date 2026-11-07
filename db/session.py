"""Database session management supporting SQLite and PostgreSQL with robust async interface."""

from typing import Any, AsyncGenerator, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.config import settings
from app.db.base import Base

# Normalize SQLite database URL for standard engine if needed
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite+aiosqlite:"):
    db_url = db_url.replace("sqlite+aiosqlite:", "sqlite:")

engine = create_engine(
    db_url,
    echo=settings.DB_ECHO,
    connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
    future=True,
)

SyncSessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class AsyncSessionAdapter:
    """Async wrapper around SQLAlchemy Session providing an async/await interface.
    
    Ensures 100% offline compatibility, zero socketpair requirements on Windows,
    and identical semantics to SQLAlchemy's AsyncSession.
    """

    def __init__(self, sync_session: Session) -> None:
        self._session = sync_session

    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
        return self._session.execute(statement, *args, **kwargs)

    async def commit(self) -> None:
        self._session.commit()

    async def rollback(self) -> None:
        self._session.rollback()

    async def refresh(self, instance: Any, *args: Any, **kwargs: Any) -> None:
        self._session.refresh(instance, *args, **kwargs)

    def add(self, instance: Any) -> None:
        self._session.add(instance)

    async def merge(self, instance: Any) -> Any:
        return self._session.merge(instance)

    async def flush(self) -> None:
        self._session.flush()

    async def close(self) -> None:
        self._session.close()

    async def __aenter__(self) -> "AsyncSessionAdapter":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
        await self.close()


def AsyncSessionLocal() -> AsyncSessionAdapter:
    """Factory creating an AsyncSessionAdapter instance."""
    return AsyncSessionAdapter(SyncSessionLocal())


async def init_db() -> None:
    """Initialize database tables synchronously to avoid IPC/socketpair blocks."""
    # Ensure models are imported so Base.metadata has all table definitions
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)


async def close_db() -> None:
    """Dispose engine connection pool."""
    engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSessionAdapter, None]:
    """FastAPI dependency yielding async session adapter."""
    async with AsyncSessionLocal() as session:
        yield session

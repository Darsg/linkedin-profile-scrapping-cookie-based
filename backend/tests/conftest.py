"""Test setup: a separate `linkedin_test` database on the compose Postgres, the
mock provider, and an in-memory queue instead of Redis."""

import os
import uuid
from collections.abc import AsyncIterator

os.environ["DATABASE_URL"] = "postgresql+asyncpg://linkedin:linkedin@localhost:5433/linkedin_test"
os.environ["PROVIDER"] = "mock"
os.environ["MOCK_DELAY_SECONDS"] = "0"

import asyncpg  # noqa: E402
import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.db import get_engine, get_sessionmaker  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


class InMemoryQueue:
    def __init__(self) -> None:
        self.enqueued: list[tuple[uuid.UUID, str]] = []

    async def enqueue(self, job_id: uuid.UUID, provider: str) -> None:
        self.enqueued.append((job_id, provider))

    async def ping(self) -> bool:
        return True


@pytest.fixture(scope="session", autouse=True)
async def _database() -> AsyncIterator[None]:
    admin = await asyncpg.connect("postgresql://linkedin:linkedin@localhost:5433/linkedin")
    if not await admin.fetchval("SELECT 1 FROM pg_database WHERE datname = 'linkedin_test'"):
        await admin.execute("CREATE DATABASE linkedin_test")
    await admin.close()

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await get_engine().dispose()


@pytest.fixture(autouse=True)
async def _clean_tables(_database: None) -> None:
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    async with get_engine().begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as s:
        yield s


@pytest.fixture
def queue() -> InMemoryQueue:
    q = InMemoryQueue()
    app.state.queue = q
    return q


@pytest.fixture
async def client(queue: InMemoryQueue) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

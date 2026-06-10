from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from main import app


class MockArqJob:
    job_id = "mock-job-001"


class MockArqPool:
    async def enqueue_job(self, _name: str, *_args, **_kwargs):
        return MockArqJob()

    async def job_info(self, _job_id: str):
        return None

    async def close(self):
        pass


@pytest.fixture(scope="session", autouse=True)
def initialize_cache():
    FastAPICache.init(InMemoryBackend())


@pytest.fixture(autouse=True)
def mock_arq_pool(monkeypatch):
    pool = MockArqPool()
    app.state.arq_pool = pool
    yield pool


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    yield None

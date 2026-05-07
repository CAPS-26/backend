from collections.abc import AsyncGenerator

import pytest

# Gunakan SQLite in-memory untuk pengujian (GeoAlchemy2 mungkin membutuhkan PostGIS)
# Untuk kesederhanaan, sesi dan operasi DB akan dimock di pengujian.
# Jika ingin integrasi asli, kita butuh DB PostGIS khusus pengujian.
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from main import app


@pytest.fixture(scope="session", autouse=True)
def initialize_cache():
    FastAPICache.init(InMemoryBackend())


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    # Ini placeholder. Pada pengujian nyata, siapkan DB pengujian.
    # Untuk sementara, DB dimock di pengujian yang membutuhkan.
    yield None

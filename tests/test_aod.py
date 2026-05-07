from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from apps.database import get_db
from main import app


@pytest.mark.asyncio
async def test_get_aod_polygon_not_found(client: AsyncClient):
    async def override_get_db():
        mock_session = AsyncMock()

        # Mock result for await db.execute()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars

        mock_session.execute.return_value = mock_result
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    response = await client.get("/api/v1/aod/polygon/")
    assert response.status_code == 404
    assert response.json()["detail"] == "Tidak ada data polygon untuk tanggal kemarin."

    app.dependency_overrides.clear()

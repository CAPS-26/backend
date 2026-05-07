from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping

from apps.aod.repositories import AodRepository


class AodApiService:
    def __init__(self, repository: AodRepository):
        self.repository = repository

    @staticmethod
    def _to_geojson_fc(rows: list[Any], value_field: str) -> dict[str, Any]:
        features = []
        for row in rows:
            shape = to_shape(row.geom)
            features.append(
                {
                    "type": "Feature",
                    "geometry": mapping(shape),
                    "properties": {value_field: getattr(row, value_field)},
                }
            )
        return {"type": "FeatureCollection", "features": features}

    async def get_aod_polygon_latest(self) -> dict[str, Any]:
        yesterday = datetime.now(UTC).date() - timedelta(days=1)
        rows = await self.repository.get_aod_polygons_by_date(yesterday)
        if not rows:
            raise HTTPException(
                status_code=404,
                detail="Tidak ada data polygon untuk tanggal kemarin.",
            )
        return self._to_geojson_fc(list(rows), "aod_value")

    async def get_aod_polygon_by_date(self, target_date: date) -> dict[str, Any]:
        rows = await self.repository.get_aod_polygons_by_date(target_date)
        if not rows:
            raise HTTPException(
                status_code=404,
                detail="Tidak ada data polygon untuk tanggal tersebut.",
            )
        return self._to_geojson_fc(list(rows), "aod_value")

    async def get_pm25_polygon_latest(self) -> dict[str, Any]:
        yesterday = datetime.now(UTC).date() - timedelta(days=1)
        rows = await self.repository.get_pm25_polygons_by_date(yesterday)
        if not rows:
            raise HTTPException(
                status_code=404,
                detail="Tidak ada data polygon untuk tanggal kemarin.",
            )
        return self._to_geojson_fc(list(rows), "pm25_value")

    async def get_pm25_polygon_by_date(self, target_date: date) -> dict[str, Any]:
        rows = await self.repository.get_pm25_polygons_by_date(target_date)
        if not rows:
            raise HTTPException(
                status_code=404,
                detail="Tidak ada data polygon untuk tanggal tersebut.",
            )
        return self._to_geojson_fc(list(rows), "pm25_value")

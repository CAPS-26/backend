from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from geoalchemy2.shape import to_shape

from apps.weather.models import PM25DataActual, WeatherData
from apps.weather.repositories import WeatherRepository


class WeatherApiService:
    def __init__(self, repository: WeatherRepository):
        self.repository = repository

    @staticmethod
    def _coords(station) -> tuple[float | None, float | None]:
        if station and station.location:
            pt = to_shape(station.location)
            return pt.y, pt.x
        return None, None

    def _weather_row(self, row: WeatherData) -> dict[str, Any]:
        latitude, longitude = self._coords(row.station)
        return {
            "station_name": row.station.name if row.station else None,
            "latitude": latitude,
            "longitude": longitude,
            "temperature": row.temperature,
            "precipitation": row.precipitation,
            "humidity": row.humidity,
            "wind_dir": row.wind_dir,
            "wind_speed": row.wind_speed,
        }

    def _pm25_actual_row(self, row: PM25DataActual) -> dict[str, Any]:
        latitude, longitude = self._coords(row.station)
        return {
            "id": row.id,
            "station_id": row.station_id,
            "station_name": row.station.name if row.station else None,
            "latitude": latitude,
            "longitude": longitude,
            "date": row.date,
            "pm25_value": row.pm25_value,
        }

    async def get_latest_weather(self) -> list[dict[str, Any]]:
        today = datetime.now(UTC).date()
        rows = await self.repository.get_weather_by_date(today)
        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"Tidak ada data cuaca untuk tanggal {today}.",
            )
        return [self._weather_row(row) for row in rows]

    async def get_weather_by_date(self, target_date) -> list[dict[str, Any]]:
        rows = await self.repository.get_weather_by_date(target_date)
        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"Tidak ada data cuaca untuk tanggal {target_date}.",
            )
        return [self._weather_row(row) for row in rows]

    async def get_latest_pm25_actual(self) -> list[dict[str, Any]]:
        today = datetime.now(UTC).date()
        rows = await self.repository.get_pm25_actual_by_date(today)
        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"Tidak ada data PM2.5 untuk tanggal {today}.",
            )
        return [self._pm25_actual_row(row) for row in rows]

    async def get_pm25_actual_by_date(self, target_date) -> list[dict[str, Any]]:
        rows = await self.repository.get_pm25_actual_by_date(target_date)
        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"Tidak ada data PM2.5 untuk tanggal {target_date}.",
            )
        return [self._pm25_actual_row(row) for row in rows]

    async def get_latest_pm25_prediction(self) -> list[dict[str, Any]]:
        today = datetime.now(UTC).date()
        rows = await self.repository.get_pm25_prediction_by_date(today)
        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"Tidak ada data PM2.5 prediksi untuk tanggal {today}.",
            )
        stations = await self.repository.get_station_map()
        return [
            {
                "id": row.id,
                "station_id": row.station_id,
                "station_name": stations.get(row.station_id, "unknown"),
                "latitude": 0.0,
                "longitude": 0.0,
                "date": row.date,
                "pm25_value": row.pm25_value,
            }
            for row in rows
        ]

    async def get_pm25_prediction_by_date(self, target_date) -> list[dict[str, Any]]:
        rows = await self.repository.get_pm25_prediction_by_date(target_date)
        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"Tidak ada data PM2.5 prediksi untuk tanggal {target_date}.",
            )
        stations = await self.repository.get_station_map()
        return [
            {
                "id": row.id,
                "station_id": row.station_id,
                "station_name": stations.get(row.station_id, "unknown"),
                "latitude": 0.0,
                "longitude": 0.0,
                "date": row.date,
                "pm25_value": row.pm25_value,
            }
            for row in rows
        ]

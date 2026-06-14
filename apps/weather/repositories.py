from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from apps.weather.models import (
    PM25DataActual,
    PM25DataPrediction,
    WeatherData,
    WeatherStation,
)


class WeatherRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_stations(self) -> Sequence[WeatherStation]:
        result = await self.db.execute(select(WeatherStation))
        return result.scalars().all()

    async def get_station_by_name(self, name: str) -> WeatherStation | None:
        result = await self.db.execute(
            select(WeatherStation).filter(WeatherStation.name.ilike(name.strip()))
        )
        return result.scalars().first()

    async def get_weather_by_date(self, target_date: date) -> Sequence[WeatherData]:
        result = await self.db.execute(
            select(WeatherData)
            .options(joinedload(WeatherData.station))
            .filter(WeatherData.date == target_date)
        )
        return result.scalars().all()

    async def get_weather_by_station_and_date(
        self, station_id: int, target_date: date
    ) -> WeatherData | None:
        result = await self.db.execute(
            select(WeatherData).filter_by(station_id=station_id, date=target_date)
        )
        return result.scalars().first()

    async def save_weather(self, weather: WeatherData):
        self.db.add(weather)
        await self.db.commit()

    async def get_pm25_actual_by_date(
        self, target_date: date
    ) -> Sequence[PM25DataActual]:
        result = await self.db.execute(
            select(PM25DataActual)
            .options(joinedload(PM25DataActual.station))
            .filter(PM25DataActual.date == target_date)
        )
        return result.scalars().all()

    async def get_pm25_actual_by_station_and_date(
        self, station_id: int, target_date: date
    ) -> PM25DataActual | None:
        result = await self.db.execute(
            select(PM25DataActual).filter_by(station_id=station_id, date=target_date)
        )
        return result.scalars().first()

    async def save_pm25_actual(self, record: PM25DataActual):
        self.db.add(record)
        await self.db.commit()

    async def get_pm25_prediction_by_date(
        self, target_date: date
    ) -> Sequence[PM25DataPrediction]:
        result = await self.db.execute(
            select(PM25DataPrediction).filter(PM25DataPrediction.date == target_date)
        )
        return result.scalars().all()

    async def get_pm25_actual_history(self) -> Sequence[PM25DataActual]:
        result = await self.db.execute(
            select(PM25DataActual)
            .options(joinedload(PM25DataActual.station))
            .order_by(PM25DataActual.date.desc())
        )
        return result.scalars().all()

    async def get_pm25_prediction_history(self) -> Sequence[PM25DataPrediction]:
        result = await self.db.execute(
            select(PM25DataPrediction)
            .order_by(PM25DataPrediction.date.desc())
        )
        return result.scalars().all()

    async def save_pm25_prediction(self, record: PM25DataPrediction):
        self.db.add(record)
        await self.db.commit()

    async def get_station_map(self) -> dict[int, str]:
        result = await self.db.execute(select(WeatherStation))
        return {s.id: s.name for s in result.scalars().all()}

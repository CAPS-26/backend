from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.aod.models import (
    AerosolOpticalDepth,
    AerosolOpticalDepthPolygon,
    PM25DataEstimate,
    PolygonDataPM25,
)


class AodRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_aod_polygons_by_date(
        self, target_date: date
    ) -> Sequence[AerosolOpticalDepthPolygon]:
        result = await self.db.execute(
            select(AerosolOpticalDepthPolygon).filter(
                AerosolOpticalDepthPolygon.date == target_date
            )
        )
        return result.scalars().all()

    async def get_pm25_polygons_by_date(
        self, target_date: date
    ) -> Sequence[PolygonDataPM25]:
        result = await self.db.execute(
            select(PolygonDataPM25).filter(PolygonDataPM25.date == target_date)
        )
        return result.scalars().all()

    async def get_all_aod_records(self) -> Sequence[AerosolOpticalDepth]:
        result = await self.db.execute(select(AerosolOpticalDepth))
        return result.scalars().all()

    async def get_pm25_estimate_by_aod_id(self, aod_id: int) -> PM25DataEstimate | None:
        result = await self.db.execute(
            select(PM25DataEstimate).filter(PM25DataEstimate.aod_id == aod_id)
        )
        return result.scalars().first()

    async def save_pm25_estimate(self, estimate: PM25DataEstimate):
        self.db.add(estimate)
        await self.db.flush()
        return estimate

    async def save_pm25_polygons(self, polygons: list[PolygonDataPM25]):
        if polygons:
            self.db.add_all(polygons)
        await self.db.commit()

    async def save_aod_record(self, record: AerosolOpticalDepth):
        self.db.add(record)
        await self.db.commit()

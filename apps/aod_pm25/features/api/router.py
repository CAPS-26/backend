"""API polygon AOD dan PM2.5."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession

from apps.aod_pm25.features.api.schemas import DateInput
from apps.aod_pm25.features.api.service import AodApiService
from apps.aod_pm25.repositories import AodRepository
from apps.database import get_db

router = APIRouter()


def _get_repository(
    db: AsyncSession = Depends(get_db),
) -> AodRepository:
    return AodRepository(db)


def _get_service(
    repo: AodRepository = Depends(_get_repository),
) -> AodApiService:
    return AodApiService(repo)


def _parse_date(date_str: str):
    try:
        return datetime.strptime(date_str, "%d-%m-%Y").date()
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Format tanggal salah. Gunakan DD-MM-YYYY (Contoh: 08-05-2026)",
        )


@router.get(
    "/polygon/",
    summary="Ambil Data Polygon AOD Kemarin",
    description="Mengembalikan data polygon AOD untuk kemarin.",
)
@cache(expire=3600)
async def get_aod_polygon(
    service: AodApiService = Depends(_get_service),
):
    return await service.get_aod_polygon_latest()


@router.post(
    "/polygon/by-date/",
    summary="Ambil Data Polygon AOD Berdasarkan Tanggal",
    description="Mengembalikan data polygon AOD berdasarkan tanggal (Format: DD-MM-YYYY).",
)
@cache(expire=86400)
async def get_aod_polygon_by_date(
    body: DateInput,
    service: AodApiService = Depends(_get_service),
):
    target_date = _parse_date(body.tanggal)
    return await service.get_aod_polygon_by_date(target_date)


@router.get(
    "/pm25/polygon/",
    summary="Ambil Data Polygon PM2.5 Kemarin",
    description="Mengembalikan data polygon PM2.5 estimasi untuk kemarin.",
)
@cache(expire=3600)
async def get_pm25_polygon(
    service: AodApiService = Depends(_get_service),
):
    return await service.get_pm25_polygon_latest()


@router.post(
    "/pm25/polygon/by-date/",
    summary="Ambil Data Polygon PM2.5 Berdasarkan Tanggal",
    description=(
        "Mengembalikan data polygon PM2.5 estimasi berdasarkan tanggal (Format: DD-MM-YYYY)."
    ),
)
@cache(expire=86400)
async def get_pm25_polygon_by_date(
    body: DateInput,
    service: AodApiService = Depends(_get_service),
):
    target_date = _parse_date(body.tanggal)
    return await service.get_pm25_polygon_by_date(target_date)

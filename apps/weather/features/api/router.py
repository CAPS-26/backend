"""API data cuaca dan PM2.5 per stasiun."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession

from apps.database import get_db
from apps.weather.features.api.schemas import (
    DateInput,
    PM25ActualOut,
    PM25PredictionOut,
    WeatherDataOut,
)
from apps.weather.features.api.service import WeatherApiService
from apps.weather.repositories import WeatherRepository

router = APIRouter()


def _get_repository(
    db: AsyncSession = Depends(get_db),
) -> WeatherRepository:
    return WeatherRepository(db)


def _get_service(
    repo: WeatherRepository = Depends(_get_repository),
) -> WeatherApiService:
    return WeatherApiService(repo)


def _parse_date(date_str: str):
    try:
        return datetime.strptime(date_str, "%d-%m-%Y").date()
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Format tanggal salah. Gunakan DD-MM-YYYY (Contoh: 08-05-2026)",
        )


@router.get(
    "/weather/",
    summary="Ambil Data Cuaca Hari Ini",
    description="Mengembalikan data cuaca dari seluruh stasiun untuk hari ini.",
)
@cache(expire=3600)
async def get_latest_weather(
    service: WeatherApiService = Depends(_get_service),
) -> list[WeatherDataOut]:
    return await service.get_latest_weather()


@router.post(
    "/weather/by-date/",
    summary="Ambil Data Cuaca Berdasarkan Tanggal",
    description="Mengembalikan data cuaca berdasarkan tanggal (Format: DD-MM-YYYY).",
)
@cache(expire=86400)
async def get_weather_by_date(
    body: DateInput,
    service: WeatherApiService = Depends(_get_service),
) -> list[WeatherDataOut]:
    target_date = _parse_date(body.date)
    return await service.get_weather_by_date(target_date)


@router.get(
    "/pm25/actual/",
    summary="Ambil Data PM2.5 Aktual Hari Ini",
)
@cache(expire=3600)
async def get_latest_pm25_actual(
    service: WeatherApiService = Depends(_get_service),
) -> list[PM25ActualOut]:
    return await service.get_latest_pm25_actual()


@router.post(
    "/pm25/actual/by-date/",
    summary="Ambil Data PM2.5 Aktual Berdasarkan Tanggal",
    description="Mengembalikan data PM2.5 aktual berdasarkan tanggal (Format: DD-MM-YYYY).",
)
@cache(expire=86400)
async def get_pm25_actual_by_date(
    body: DateInput,
    service: WeatherApiService = Depends(_get_service),
) -> list[PM25ActualOut]:
    target_date = _parse_date(body.date)
    return await service.get_pm25_actual_by_date(target_date)


@router.get(
    "/pm25/prediction/",
    summary="Ambil Data PM2.5 Prediksi Hari Ini",
)
@cache(expire=3600)
async def get_latest_pm25_prediction(
    service: WeatherApiService = Depends(_get_service),
) -> list[PM25PredictionOut]:
    return await service.get_latest_pm25_prediction()


@router.post(
    "/pm25/prediction/by-date/",
    summary="Ambil Data PM2.5 Prediksi Berdasarkan Tanggal",
    description="Mengembalikan data PM2.5 prediksi berdasarkan tanggal (Format: DD-MM-YYYY).",
)
@cache(expire=86400)
async def get_pm25_prediction_by_date(
    body: DateInput,
    service: WeatherApiService = Depends(_get_service),
) -> list[PM25PredictionOut]:
    target_date = _parse_date(body.date)
    return await service.get_pm25_prediction_by_date(target_date)


@router.get(
    "/pm25/actual/history/",
    summary="Ambil Riwayat Data PM2.5 Aktual",
)
@cache(expire=3600)
async def get_pm25_actual_history(
    service: WeatherApiService = Depends(_get_service),
) -> list[PM25ActualOut]:
    return await service.get_pm25_actual_history()


@router.get(
    "/pm25/prediction/history/",
    summary="Ambil Riwayat Data PM2.5 Prediksi",
)
@cache(expire=3600)
async def get_pm25_prediction_history(
    service: WeatherApiService = Depends(_get_service),
) -> list[PM25PredictionOut]:
    return await service.get_pm25_prediction_history()

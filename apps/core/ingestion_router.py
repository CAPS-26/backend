"""API untuk memicu ingestion data secara manual."""

from fastapi import APIRouter
from apps.weather.features.ingestion.weather_fetcher import fetch_weather_data
from apps.aod.features.ingestion.himawari_ingestor import getDataHimawari
from apps.weather.features.ingestion.pm25_crawler import get_ispu_pm25_now
from apps.aod.features.estimation.service import estimatePm25

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])

@router.post("/weather/fetch-latest", summary="Trigger Ingestion Cuaca")
async def trigger_weather_fetch():
    """Memicu pengambilan data cuaca terbaru dari Visual Crossing API."""
    await fetch_weather_data()
    return {"status": "success", "message": "Weather ingestion triggered"}

@router.post("/aod/fetch-latest", summary="Trigger Ingestion AOD (Himawari)")
async def trigger_aod_fetch():
    """Memicu pengambilan data AOD terbaru dari Himawari."""
    await getDataHimawari()
    return {"status": "success", "message": "AOD ingestion triggered"}

@router.post("/pm25-crawler/trigger", summary="Trigger Crawler PM2.5 (ISPU)")
async def trigger_pm25_crawler():
    """Memicu crawler PM2.5 dari situs ISPU Jakarta."""
    await get_ispu_pm25_now()
    return {"status": "success", "message": "PM2.5 crawler triggered"}

@router.post("/pm25-estimation/trigger", summary="Trigger Estimasi PM2.5")
async def trigger_pm25_estimation():
    """Memicu proses estimasi PM2.5 berdasarkan data AOD dan Cuaca."""
    await estimatePm25()
    return {"status": "success", "message": "PM2.5 estimation triggered"}

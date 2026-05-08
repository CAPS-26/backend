"""API untuk memicu ingestion data secara manual via Celery task queue."""

from fastapi import APIRouter
from apps.core.tasks import (
    task_fetch_weather,
    task_fetch_himawari,
    task_crawl_pm25,
    task_estimate_pm25,
)

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])

@router.post("/weather/fetch-latest", summary="Trigger Ingestion Cuaca (Background)")
async def trigger_weather_fetch():
    """Memicu pengambilan data cuaca terbaru ke antrian background Celery."""
    task_fetch_weather.delay()
    return {"status": "success", "message": "Weather ingestion task queued"}

@router.post("/aod/fetch-latest", summary="Trigger Ingestion AOD (Background)")
async def trigger_aod_fetch():
    """Memicu pengambilan data AOD terbaru ke antrian background Celery."""
    task_fetch_himawari.delay()
    return {"status": "success", "message": "AOD ingestion task queued"}

@router.post("/pm25-crawler/trigger", summary="Trigger Crawler PM2.5 (Background)")
async def trigger_pm25_crawler():
    """Memicu crawler PM2.5 ke antrian background Celery."""
    task_crawl_pm25.delay()
    return {"status": "success", "message": "PM2.5 crawler task queued"}

@router.post("/pm25-estimation/trigger", summary="Trigger Estimasi PM2.5 (Background)")
async def trigger_pm25_estimation():
    """Memicu proses estimasi PM2.5 ke antrian background Celery."""
    task_estimate_pm25.delay()
    return {"status": "success", "message": "PM2.5 estimation task queued"}

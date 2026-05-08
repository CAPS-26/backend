import asyncio
import logging
from apps.core.celery_app import celery_app
from apps.weather.features.ingestion.weather_fetcher import fetch_weather_data
from apps.aod.features.ingestion.himawari_ingestor import getDataHimawari
from apps.weather.features.ingestion.pm25_crawler import get_ispu_pm25_now
from apps.aod.features.estimation.service import estimatePm25

logger = logging.getLogger(__name__)

def run_async(coro):
    """Helper untuk menjalankan coroutine di dalam task Celery."""
    try:
        return asyncio.run(coro)
    except Exception as e:
        logger.error(f"Error running async task: {e}")
        raise

@celery_app.task(name="apps.core.tasks.task_fetch_weather")
def task_fetch_weather():
    logger.info("Starting weather fetch task...")
    return run_async(fetch_weather_data())

@celery_app.task(name="apps.core.tasks.task_fetch_himawari")
def task_fetch_himawari():
    logger.info("Starting Himawari ingestion task...")
    return run_async(getDataHimawari())

@celery_app.task(name="apps.core.tasks.task_crawl_pm25")
def task_crawl_pm25():
    logger.info("Starting PM2.5 crawler task...")
    return run_async(get_ispu_pm25_now())

@celery_app.task(name="apps.core.tasks.task_estimate_pm25")
def task_estimate_pm25():
    logger.info("Starting PM2.5 estimation task...")
    return run_async(estimatePm25())

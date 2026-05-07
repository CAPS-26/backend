from apscheduler.schedulers.asyncio import AsyncIOScheduler

from apps.aod.features.estimation.service import estimatePm25
from apps.aod.features.ingestion.himawari_ingestor import getDataHimawari
from apps.weather.features.ingestion.pm25_crawler import get_ispu_pm25_now
from apps.weather.features.ingestion.weather_fetcher import fetch_weather_data
from config.settings import settings


def create_scheduler() -> AsyncIOScheduler:
    return AsyncIOScheduler(
        timezone=settings.scheduler_timezone,
        job_defaults={"coalesce": True, "max_instances": 1},
    )


def register_jobs(scheduler: AsyncIOScheduler) -> None:
    # AsyncIOScheduler mendukung fungsi coroutine; daftarkan callable async
    scheduler.add_job(fetch_weather_data, "cron", hour=8, minute=35, id="fetch_weather")
    scheduler.add_job(getDataHimawari, "cron", hour=8, minute=35, id="fetch_himawari")
    scheduler.add_job(get_ispu_pm25_now, "cron", hour=12, minute=0, id="crawl_pm25")
    scheduler.add_job(estimatePm25, "cron", hour=8, minute=50, id="estimate_pm25")

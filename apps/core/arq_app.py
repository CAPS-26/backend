from zoneinfo import ZoneInfo

from arq.connections import RedisSettings
from arq.cron import cron

from apps.core.tasks import (
    task_crawl_pm25,
    task_estimate_pm25,
    task_fetch_himawari,
    task_fetch_weather,
    task_predict_pm25_all,
)
from config.settings import settings


def _build_redis() -> RedisSettings:
    if settings.redis_url:
        return RedisSettings.from_dsn(settings.redis_url)
    return RedisSettings(
        host=settings.redis_host,
        port=settings.redis_port,
        database=settings.redis_db,
    )


class WorkerSettings:
    redis_settings = _build_redis()
    max_jobs = settings.arq_max_jobs
    job_timeout = settings.arq_job_timeout
    keep_result = settings.arq_keep_result
    timezone = ZoneInfo(settings.scheduler_timezone)

    functions = [
        task_fetch_weather,
        task_fetch_himawari,
        task_crawl_pm25,
        task_estimate_pm25,
        task_predict_pm25_all,
    ]

    cron_jobs = [
        cron(task_fetch_weather, hour={5, 11, 17}, minute=0),
        cron(task_fetch_himawari, hour={5, 11, 17}, minute=5),
        cron(task_estimate_pm25, hour={5, 11, 17}, minute=30),
        cron(task_crawl_pm25, minute=10),
        cron(task_predict_pm25_all, hour={5, 11, 17}, minute=45),
    ]

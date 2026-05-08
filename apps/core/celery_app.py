import asyncio
from celery import Celery
from celery.schedules import crontab
from config.settings import settings

# Inisialisasi Celery
redis_url = settings.redis_url or f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"

celery_app = Celery(
    "caps_tasks",
    broker=redis_url,
    backend=redis_url,
)

# Konfigurasi Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.scheduler_timezone,
    enable_utc=True,
    # Konfigurasi Penjadwalan
    beat_schedule={
        # Ambil data cuaca & satelit 3x sehari (Pagi, Siang, Sore)
        "fetch-weather-active-hours": {
            "task": "apps.core.tasks.task_fetch_weather",
            "schedule": crontab(hour="5,11,17", minute=0),
        },
        "fetch-himawari-active-hours": {
            "task": "apps.core.tasks.task_fetch_himawari",
            "schedule": crontab(hour="5,11,17", minute=5),
        },
        # Estimasi PM2.5 dilakukan setelah data cuaca & AOD tersedia
        "estimate-pm25-active-hours": {
            "task": "apps.core.tasks.task_estimate_pm25",
            "schedule": crontab(hour="5,11,17", minute=30),
        },
        # Crawler PM2.5 ISPU dijalankan setiap jam agar selalu update
        "crawl-pm25-hourly": {
            "task": "apps.core.tasks.task_crawl_pm25",
            "schedule": crontab(minute=10),
        },
    },
)

# Auto-discover tasks dari module yang ditentukan
celery_app.autodiscover_tasks(["apps.core"])

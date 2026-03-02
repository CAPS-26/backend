"""
FastAPI application entry point.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from apps.aod.features.api.router import router as aod_router
from apps.weather.features.api.router import router as weather_router

# ---------------------------------------------------------------------------
# Scheduled jobs
# ---------------------------------------------------------------------------

scheduler = BackgroundScheduler()


def _register_jobs():
    from apps.weather.features.ingestion.weather_fetcher import fetch_weather_data
    from apps.aod.features.ingestion.himawari_ingestor import getDataHimawari
    from apps.weather.features.ingestion.pm25_crawler import get_ispu_pm25_now
    from apps.aod.features.estimation.service import estimatePm25

    # Daily at 08:35 — fetch weather & download satellite data
    scheduler.add_job(fetch_weather_data, "cron", hour=8, minute=35, id="fetch_weather")
    scheduler.add_job(getDataHimawari, "cron", hour=8, minute=35, id="fetch_himawari")

    # Daily at 12:00 — scrape ISPU PM2.5
    scheduler.add_job(get_ispu_pm25_now, "cron", hour=12, minute=0, id="crawl_pm25")

    # Daily at 08:50 — run PM2.5 spatial estimation
    scheduler.add_job(estimatePm25, "cron", hour=8, minute=50, id="estimate_pm25")


# ---------------------------------------------------------------------------
# App lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    _register_jobs()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="PM2.5 & AOD Jakarta API",
    description="Air quality monitoring: AOD satellite data & weather-based PM2.5 estimation.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(aod_router, prefix="/api/aod", tags=["AOD"])
app.include_router(weather_router, prefix="/api/weather", tags=["Weather"])


@app.get("/", include_in_schema=False)
def root():
    return {"status": "ok", "docs": "/docs"}
